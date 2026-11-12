-- PostgreSQL 16 DDL Schema for Payment Service Migration
-- Specification: PostgreSQL 16 + uuidv7 primary keys

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY, -- uuidv7 time-ordered unique identifier
    customer_id VARCHAR(64) NOT NULL,
    amount_cents BIGINT NOT NULL CHECK (amount_cents >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_audit_log (
    log_id UUID PRIMARY KEY, -- uuidv7
    payment_id UUID NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    previous_state VARCHAR(32),
    new_state VARCHAR(32) NOT NULL,
    changed_by VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_idempotency ON payments(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_audit_payment_id ON payment_audit_log(payment_id);
