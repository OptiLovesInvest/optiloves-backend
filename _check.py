import sys
p="app.py"
try:
    compile(open(p,"rb").read(), p, "exec")
    print("OK: app.py compiles")
except SyntaxError as e:
    print(f"ERROR: {type(e).__name__} at line {e.lineno}, col {e.offset}")
    with open(p,"r",encoding="utf-8",errors="replace") as f:
        lines=f.readlines()
    s=max(0,(e.lineno or 1)-3); t=min(len(lines),(e.lineno or 1)+2)
    for i in range(s,t):
        print(f"{i+1:4}: {lines[i].rstrip()}")
    sys.exit(1)