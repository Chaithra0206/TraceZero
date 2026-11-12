import hashlib
from pathlib import Path
from typing import Dict, List


def scan_shard_bytes(shard_dir: Path, forbidden_strings: List[str]) -> int:
    """Scans every file in the shard (.sqlite, -wal, .okf.md, sources/*.txt) at the raw byte level."""
    total_matches = 0
    needles = [s.encode("utf-8").lower() for s in forbidden_strings if s and len(s) >= 3]
    if not needles:
        return 0
    for path in shard_dir.rglob("*"):
        if path.is_file():
            raw = path.read_bytes().lower()
            for needle in needles:
                total_matches += raw.count(needle)
    return total_matches


def compute_shard_hashes(shard_dir: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for path in sorted(shard_dir.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(shard_dir))
            hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes
