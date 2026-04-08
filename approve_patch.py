
def get_db():
    return psycopg2.connect(os.environ.get("PG_DSN"))

@app.route("/admin/payouts/<quarter>/approve", methods=["POST"])
def payout_approve(quarter):
    if request.headers.get("x-api-key") != os.environ.get("API_KEY"):
        return jsonify({"error": "unauthorized"}), 401

    rpc_url = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
    known_wallets = [w.strip() for w in os.environ.get("KNOWN_WALLETS", "").split(",") if w.strip()]

    if not known_wallets:
        return jsonify({"error": "KNOWN_WALLETS is empty"}), 400

    line_items = []
    total_tokens = 0
    total_usdc = Decimal("0.00")

    for wallet in known_wallets:
        try:
            resp = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet,
                        {"mint": MINT},
                        {"encoding": "jsonParsed"}
                    ]
                },
                timeout=10
            )

            if resp.status_code != 200:
                raise Exception(f"RPC error {resp.status_code}")

            data = resp.json()
            accounts = data.get("result", {}).get("value", [])
            balance = 0

            for acc in accounts:
                amount = acc["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"]
                balance += int(amount or 0)

            usdc = calculate_payout(balance)
            total_tokens += balance
            total_usdc += usdc

            line_items.append({
                "wallet": wallet,
                "tokens_held": balance,
                "usdc_amount": usdc
            })

        except Exception as e:
            return jsonify({"error": f"RPC failed for {wallet}: {str(e)}"}), 500

    if not line_items:
        return jsonify({"error": "no payout line items generated"}), 400

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, status FROM payout_runs WHERE quarter = %s",
            (quarter,)
        )
        existing = cur.fetchone()
        if existing:
            return jsonify({
                "error": "payout run already exists",
                "quarter": quarter,
                "run_id": existing[0],
                "status": existing[1]
            }), 409

        cur.execute("""
            INSERT INTO payout_runs
                (quarter, total_wallets, total_tokens, total_usdc, status)
            VALUES (%s, %s, %s, %s, 'draft')
            RETURNING id
        """, (quarter, len(line_items), total_tokens, str(total_usdc)))

        run_id = cur.fetchone()[0]

        for item in line_items:
            cur.execute("""
                INSERT INTO payout_line_items
                    (payout_run_id, wallet_address, mint, tokens_held, usdc_amount, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (
                run_id,
                item["wallet"],
                MINT,
                item["tokens_held"],
                str(item["usdc_amount"])
            ))

        cur.execute("""
            UPDATE payout_runs
            SET status = 'approved', approved_at = NOW()
            WHERE id = %s
        """, (run_id,))

        conn.commit()

        return jsonify({
            "quarter": quarter,
            "run_id": run_id,
            "total_wallets": len(line_items),
            "total_tokens": total_tokens,
            "total_usdc": str(total_usdc),
            "status": "approved"
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"DB error: {str(e)}"}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route("/admin/payouts/<quarter>/report", methods=["GET"])
def payout_report(quarter):
    if request.headers.get("x-api-key") != os.environ.get("API_KEY"):
        return jsonify({"error": "unauthorized"}), 401

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, quarter, total_wallets, total_tokens, total_usdc, status, created_at, approved_at
            FROM payout_runs
            WHERE quarter = %s
        """, (quarter,))
        run = cur.fetchone()

        if not run:
            return jsonify({"error": "payout run not found"}), 404

        cur.execute("""
            SELECT wallet_address, mint, tokens_held, usdc_amount, status, tx_signature, error_message
            FROM payout_line_items
            WHERE payout_run_id = %s
            ORDER BY wallet_address
        """, (run[0],))
        items = cur.fetchall()

        return jsonify({
            "run_id": run[0],
            "quarter": run[1],
            "total_wallets": run[2],
            "total_tokens": run[3],
            "total_usdc": str(run[4]),
            "status": run[5],
            "created_at": str(run[6]) if run[6] else None,
            "approved_at": str(run[7]) if run[7] else None,
            "line_items": [
                {
                    "wallet": i[0],
                    "mint": i[1],
                    "tokens_held": i[2],
                    "usdc_amount": str(i[3]),
                    "status": i[4],
                    "tx_signature": i[5],
                    "error_message": i[6]
                }
                for i in items
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": f"DB error: {str(e)}"}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
