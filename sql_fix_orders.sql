-- Create columns if missing
do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='orders' and column_name='order_id'
  ) then
    alter table public.orders add column order_id text;
  end if;

  if not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='orders' and column_name='unit_price_usd'
  ) then
    alter table public.orders add column unit_price_usd numeric(12,2);
  end if;
end $$;

-- If there's an "id" column, backfill order_id from it (once)
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='orders' and column_name='id'
  ) then
    update public.orders
       set order_id = coalesce(order_id, id::text)
     where order_id is null;
  end if;
end $$;

-- Make order_id NOT NULL after backfill (safe if all rows filled)
alter table public.orders
  alter column order_id set not null;

-- Ensure uniqueness (don’t replace PKs; just add a unique index)
do $$
begin
  if not exists (
    select 1 from pg_indexes
     where schemaname='public' and indexname='orders_order_id_key'
  ) then
    create unique index orders_order_id_key on public.orders(order_id);
  end if;
end $$;
