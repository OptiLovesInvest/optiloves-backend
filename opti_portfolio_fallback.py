from flask import Blueprint, jsonify, request
import os, json, time, urllib.request

bp = Blueprint("opti_pf", __name__, url_prefix="/api")

def _rpc(url, method, params):
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as r: return json.loads(r.read().decode())

def _rpc_url(): return os.getenv("SOLANA_RPC","https://api.mainnet-beta.solana.com")
def _mints():
    ms=[m.strip() for m in os.getenv("OPTILOVES_MINTS","").split(",") if m.strip()]
    return ms or ["5ihsE55yaFFZXoizZKv5xsd6YjEuvaXiiMr2FLjQztN9"]

def _items(owner):
    out=[]; rpc=_rpc_url()
    for m in _mints():
        resp=_rpc(rpc,"getTokenAccountsByOwner",[owner,{"mint":m},{"encoding":"jsonParsed"}])
        total=0.0
        for v in resp.get("result",{}).get("value",[]):
            ui=v["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmount",0) or 0
            try: total+=float(ui)
            except: pass
        price=float(os.getenv("OPTILOVES_BASE_PRICE_USD","50"))
        out.append({"mint":m,"balance":total,"price":price,"estValue":round(total*price,2)})
    return out

@bp.get("/portfolio/<owner>")
def by_path(owner): return jsonify({"owner":owner,"items":_items(owner),"ts":int(time.time()*1000)})

@bp.get("/portfolio")
def by_query():
    owner=(request.args.get("owner","") or "").strip()
    return jsonify({"owner":owner,"items":_items(owner),"ts":int(time.time()*1000)})
