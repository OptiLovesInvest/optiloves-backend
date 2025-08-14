import os, json, requests, gradio as gr

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")

def _get(url, **kw):
    try:
        r = requests.get(url, timeout=10, **kw); r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, str(e)

def _post(url, payload):
    try:
        r = requests.post(url, json=payload, timeout=20); r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, str(e)

def fetch_properties():
    ok, data = _get(f"{BACKEND}/properties")
    if not ok: return [], f"Error: {data}"
    # label visible to user, value = id
    return [(f"{p.get('title','(untitled)')} ({p.get('id')})", p.get('id')) for p in data], f"Loaded {len(data)} properties."

def fetch_price():
    ok, data = _get(f"{BACKEND}/price")
    if ok and isinstance(data, dict):
        return data.get("token_price"), data.get("available_tokens"), ""
    return 50, 4999, "Using demo price (no /price endpoint)."

def airdrop_sol(wallet):
    if not wallet: return "Enter a devnet wallet address."
    ok, data = _post(f"{BACKEND}/airdrop", {"wallet": wallet})
    return data if ok else f"Error: {data}"

def buy_tokens(property_id, wallet, qty):
    if not property_id: return "Choose a property."
    if not wallet: return "Enter your wallet address."
    if (qty or 0) <= 0: return "Quantity must be at least 1."
    ok, data = _post(f"{BACKEND}/buy", {"property_id": property_id, "wallet": wallet, "quantity": int(qty)})
    return json.dumps(data, indent=2) if ok else f"Error: {data}"

def build_ui():
    with gr.Blocks(title="Optiloves-Invest — Demo") as demo:
        gr.Markdown("## Optiloves-Invest — MVP Demo (Gradio)\nProperties, price, airdrop and buy flow.")

        backend_box = gr.Textbox(label="Backend URL", value=BACKEND, interactive=False)
        refresh = gr.Button("↻ Refresh")

        props_cache = gr.Textbox(visible=False)
        properties_dropdown = gr.Dropdown(label="Available Properties", choices=[], value=None, interactive=True)
        selected_property_id = gr.Textbox(label="Selected Property ID", interactive=False)

        price_box = gr.Number(label="Token Price (USD)", precision=2)
        available_box = gr.Number(label="Available Tokens", precision=0)

        gr.Markdown("### Airdrop (devnet)")
        wallet_airdrop = gr.Textbox(label="Wallet (devnet)", placeholder="Your Phantom devnet address")
        btn_airdrop = gr.Button("Get 1 SOL (devnet)")
        airdrop_result = gr.Textbox(label="Airdrop Result", lines=3)

        gr.Markdown("### Buy Tokens")
        wallet_buy = gr.Textbox(label="Buyer Wallet", placeholder="Your Phantom address")
        qty = gr.Number(label="Quantity", value=1, precision=0)
        btn_buy = gr.Button("Buy")
        buy_result = gr.Code(label="Purchase Response", language="json")

        status = gr.Textbox(label="Status", interactive=False)

        def _refresh():
            props, note = fetch_properties()
            mapping = {label: pid for (label, pid) in props}
            mapping_json = json.dumps(mapping)
            price, available, msg = fetch_price()
            dropdown = gr.update(choices=list(mapping.keys()), value=(next(iter(mapping)) if mapping else None))
            chosen_id = (next(iter(mapping.values())) if mapping else "")
            return dropdown, mapping_json, chosen_id, price, available, BACKEND, "\n".join([s for s in [note, msg] if s])

        refresh.click(_refresh, outputs=[properties_dropdown, props_cache, selected_property_id, price_box, available_box, backend_box, status])
        demo.load(_refresh, outputs=[properties_dropdown, props_cache, selected_property_id, price_box, available_box, backend_box, status])

        def _dropdown_changed(label_choice, mapping_json):
            try: return json.loads(mapping_json).get(label_choice, "")
            except Exception: return ""
        properties_dropdown.change(_dropdown_changed, [properties_dropdown, props_cache], [selected_property_id])

        btn_airdrop.click(airdrop_sol, [wallet_airdrop], [airdrop_result])
        btn_buy.click(buy_and_refresh, [selected_property_id, wallet_buy, qty], [buy_result, available_box])

    return demo

def buy_and_refresh(property_id, wallet, qty):
    result = buy_tokens(property_id, wallet, qty)
    _, available, _ = fetch_price()
    return result, available


if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860, share=True)


