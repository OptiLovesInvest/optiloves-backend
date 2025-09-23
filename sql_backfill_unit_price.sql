ALTER TABLE orders
  ALTER COLUMN unit_price_usd DROP NOT NULL;
UPDATE orders
  SET unit_price_usd = 50
  WHERE unit_price_usd IS NULL;
