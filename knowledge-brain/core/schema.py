import hashlib
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union
import sqlite_vec
from core.contracts import ClaimRecord, SourceRecord, TrustTier


def serialize_f32(vector: List[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class ShardManager:
    def __init__(self, root_dir: str = "memory_root"):
        self.root_dir = Path(root_dir)

    def get_shard_dir(self, namespace: str) -> Path:
        shard_dir = self.root_dir / namespace.strip("/")
        (shard_dir / "sources").mkdir(parents=True, exist_ok=True)
        return shard_dir

    def get_connection(self, namespace: str) -> sqlite3.Connection:
        db_path = self.get_shard_dir(namespace) / "index.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA secure_delete = ON;")
        conn.execute("PRAGMA foreign_keys = ON;")
        self._init_tables(conn)
        return conn

    def _init_tables(self, conn: sqlite3.Connection):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources_index (
                source_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                origin TEXT NOT NULL,
                trust_tier INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entity_aliases (
                alias TEXT PRIMARY KEY,
                canonical_subject TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims_index (
                claim_id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object_val TEXT NOT NULL,
                status TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                source_id TEXT NOT NULL REFERENCES sources_index(source_id),
                byte_start INTEGER NOT NULL,
                byte_end INTEGER NOT NULL,
                okf_file TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lineage_index (
                claim_id TEXT PRIMARY KEY REFERENCES claims_index(claim_id) ON DELETE CASCADE,
                vec_rowid INTEGER NOT NULL,
                fts_rowid INTEGER NOT NULL,
                okf_file TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suppression_hashes (
                fact_hmac TEXT PRIMARY KEY,
                deleted_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS fts_claims USING fts5(
                subject, predicate, object_val
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS vec_claims USING vec0(
                embedding float[384]
            );
        """)
        conn.commit()

    def append_raw_source(
        self,
        namespace: str,
        source_id: str,
        filename: str,
        text: str,
        origin: Union[str, TrustTier] = "user",
        trust_tier: Optional[TrustTier] = None,
    ) -> SourceRecord:
        # Support both 6-arg (namespace, source_id, filename, text, origin, trust_tier)
        # and 5-arg (namespace, filename, text, origin, trust_tier) call signatures
        if trust_tier is None and isinstance(origin, (TrustTier, int)):
            actual_trust_tier = TrustTier(origin)
            actual_origin = text
            actual_text = filename
            actual_filename = source_id
            actual_source_id = (
                f"src_{hashlib.sha256(f'{namespace}:{actual_filename}:{actual_text}'.encode()).hexdigest()[:12]}"
            )
        else:
            actual_source_id = source_id
            actual_filename = filename
            actual_text = text
            actual_origin = str(origin)
            actual_trust_tier = trust_tier if trust_tier is not None else TrustTier.USER

        shard_dir = self.get_shard_dir(namespace)
        rel_path = f"sources/{actual_filename}"
        abs_path = shard_dir / rel_path

        # Append or write raw text on filesystem (Zero DB text bloat)
        mode = "a" if abs_path.exists() else "w"
        with open(abs_path, mode, encoding="utf-8") as f:
            if mode == "a":
                f.write("\n")
            f.write(actual_text)

        file_bytes = abs_path.read_bytes()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()
        now = datetime.now(timezone.utc).isoformat()

        record = SourceRecord(
            source_id=actual_source_id,
            file_path=rel_path,
            sha256_hash=sha256_hash,
            origin=actual_origin,
            trust_tier=actual_trust_tier,
            created_at=now,
        )

        with self.get_connection(namespace) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sources_index
                   (source_id, file_path, sha256_hash, origin, trust_tier, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    record.source_id,
                    record.file_path,
                    record.sha256_hash,
                    record.origin,
                    int(record.trust_tier),
                    record.created_at,
                ),
            )
            conn.commit()
        return record

    def insert_claim_with_lineage(self, claim: ClaimRecord, embedding: List[float]):
        with self.get_connection(claim.namespace) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO claims_index
                   (claim_id, namespace, subject, predicate, object_val, status, valid_from, valid_to, source_id, byte_start, byte_end, okf_file)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    claim.claim_id,
                    claim.namespace,
                    claim.subject,
                    claim.predicate,
                    claim.object_val,
                    str(claim.status.value),
                    claim.valid_from,
                    claim.valid_to,
                    claim.source_id,
                    claim.byte_start,
                    claim.byte_end,
                    claim.okf_file,
                ),
            )
            cur.execute(
                "INSERT INTO fts_claims (subject, predicate, object_val) VALUES (?, ?, ?)",
                (claim.subject, claim.predicate, claim.object_val),
            )
            fts_rowid = cur.lastrowid

            cur.execute(
                "INSERT INTO vec_claims (rowid, embedding) VALUES (?, ?)",
                (fts_rowid, serialize_f32(embedding)),
            )
            vec_rowid = fts_rowid

            cur.execute(
                "INSERT INTO lineage_index (claim_id, vec_rowid, fts_rowid, okf_file) VALUES (?, ?, ?, ?)",
                (claim.claim_id, vec_rowid, fts_rowid, claim.okf_file),
            )
            conn.commit()


def close_all_shards() -> None:
    """Flush and close active shard resources if needed."""
    pass
