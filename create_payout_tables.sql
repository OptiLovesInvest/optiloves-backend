CREATE TABLE IF NOT EXISTS payout_runs (
    id SERIAL PRIMARY KEY,
    quarter TEXT NOT NULL UNIQUE,
    total_wallets INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_usdc NUMERIC(12,2) DEFAULT 0.00,
    status TEXT NOT NULL DEFAULT 'draft',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT payout_runs_status_chk CHECK (status IN ('draft','approved','executing','complete','failed'))
);

CREATE TABLE IF NOT EXISTS payout_line_items (
    id SERIAL PRIMARY KEY,
    payout_run_id INTEGER NOT NULL REFERENCES payout_runs(id) ON DELETE CASCADE,
    wallet_address TEXT NOT NULL,
    mint TEXT NOT NULL,
    tokens_held INTEGER NOT NULL,
    usdc_amount NUMERIC(10,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    tx_signature TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT payout_line_items_status_chk CHECK (status IN ('pending','sent','failed','skipped')),
    UNIQUE(payout_run_id, wallet_address)
);

CREATE INDEX IF NOT EXISTS idx_payout_runs_quarter ON payout_runs(quarter);
CREATE INDEX IF NOT EXISTS idx_payout_items_run_id ON payout_line_items(payout_run_id);
