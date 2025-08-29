create extension if not exists pgcrypto;

create table if not exists snapshots (
  day date not null,
  mint text not null,
  wallet text not null,
  balance numeric(20,6) not null,
  primary key (day, mint, wallet)
);

create table if not exists payout_ledgers (
  id uuid primary key default gen_random_uuid(),
  quarter text not null,
  created_at timestamptz not null default now(),
  status text not null check (status in ('draft','approved','executed','failed','canceled')),
  total_usdc_cents integer not null default 0,
  hash text not null
);

create table if not exists payout_items (
  ledger_id uuid references payout_ledgers(id) on delete cascade,
  wallet text not null,
  mint text not null,
  days_held integer not null,
  payout_cents integer not null,
  txid text,
  primary key (ledger_id, wallet, mint)
);
