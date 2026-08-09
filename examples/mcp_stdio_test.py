"""End-to-end stdio test of ableton-live-mcp server, no Ableton required."""
import json, subprocess, sys, threading, time, queue

REPO = r"C:\Users\Kim\source\repos\ableton-live-mcp"

proc = subprocess.Popen(
    ["uv", "run", "ableton-live-mcp"],
    cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", bufsize=1,
)

out_q = queue.Queue()
err_lines = []

def reader(stream, q):
    for line in stream:
        q.put(line)
    q.put(None)

def err_reader(stream):
    for line in stream:
        err_lines.append(line.rstrip())

threading.Thread(target=reader, args=(proc.stdout, out_q), daemon=True).start()
threading.Thread(target=err_reader, args=(proc.stderr,), daemon=True).start()

findings = []

def send_raw(text):
    proc.stdin.write(text + "\n")
    proc.stdin.flush()

def recv(timeout=15):
    try:
        line = out_q.get(timeout=timeout)
    except queue.Empty:
        return ("TIMEOUT", None)
    if line is None:
        return ("EOF", None)
    return ("OK", line)

def rpc(req, timeout=15):
    send_raw(json.dumps(req))
    status, line = recv(timeout)
    return status, line

def report(name, ok, detail=""):
    findings.append({"check": name, "ok": ok, "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (": " + str(detail) if detail else ""), flush=True)

# ---- 1. initialize ----
t0 = time.time()
status, line = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05",
                               "capabilities": {},
                               "clientInfo": {"name": "test-client", "version": "0.0.1"}}},
                   timeout=60)
startup_s = time.time() - t0
if status != "OK":
    report("initialize", False, f"{status}; stderr={err_lines[-5:]}")
    proc.kill(); sys.exit(1)
resp = json.loads(line)
r = resp.get("result", {})
report("initialize responds", True, f"{startup_s:.2f}s startup+response")
report("serverInfo present", "serverInfo" in r, r.get("serverInfo"))
report("instructions present", bool(r.get("instructions")), f"{len(r.get('instructions',''))} chars")
report("protocolVersion echoed", r.get("protocolVersion") == "2024-11-05", r.get("protocolVersion"))
report("capabilities.tools", "tools" in r.get("capabilities", {}), r.get("capabilities"))

# ---- notifications/initialized (no response expected) ----
send_raw(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
status, line = recv(timeout=2)
report("initialized notification produces no response", status == "TIMEOUT",
       f"got: {line[:120] if line else status}")

# ---- 2. tools/list ----
status, line = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
if status != "OK":
    report("tools/list", False, status); proc.kill(); sys.exit(1)
list_bytes = len(line.encode("utf-8"))
resp = json.loads(line)
tools = resp["result"]["tools"]
report("tools/list responds", True, f"{len(tools)} tools, {list_bytes} bytes raw response")

bad = []
desc_lens = []
for t in tools:
    problems = []
    if not isinstance(t.get("name"), str) or not t["name"]:
        problems.append("bad name")
    if not isinstance(t.get("description"), str) or not t["description"].strip():
        problems.append("empty description")
    s = t.get("inputSchema")
    if not isinstance(s, dict):
        problems.append("inputSchema not an object")
    elif s.get("type") != "object":
        problems.append(f"inputSchema.type={s.get('type')!r}")
    if problems:
        bad.append((t.get("name"), problems))
    desc_lens.append((t.get("name"), len(t.get("description", "")), len(json.dumps(t, separators=(",", ":")).encode())))
report("all tool schemas valid (type==object, name+description non-empty)", not bad, bad or f"{len(tools)} tools OK")
print("TOOLS:", json.dumps([t["name"] for t in tools]), flush=True)
desc_lens.sort(key=lambda x: -x[2])
print("LARGEST TOOL DEFS (name, desc chars, total bytes):", desc_lens[:5], flush=True)

# ---- 3. live_ping without Ableton ----
t0 = time.time()
status, line = rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "live_ping", "arguments": {"timeout": 2}}}, timeout=30)
dt = time.time() - t0
if status != "OK":
    report("live_ping (no Ableton)", False, f"{status} after {dt:.1f}s")
else:
    resp = json.loads(line)
    if "error" in resp:
        report("live_ping (no Ableton) -> JSON-RPC error", True,
               f"{dt:.2f}s; code={resp['error']['code']}; msg={resp['error']['message'][:200]}")
    else:
        res = resp.get("result", {})
        report("live_ping (no Ableton) -> tool result", bool(res.get("isError")),
               f"{dt:.2f}s; isError={res.get('isError')}; content={str(res)[:200]}")

# ---- 4a. unknown method ----
status, line = rpc({"jsonrpc": "2.0", "id": 4, "method": "bogus/method"})
ok = status == "OK" and "error" in json.loads(line)
report("unknown method -> error", ok, line.strip()[:160] if line else status)

# ---- 4b. nonexistent tool ----
status, line = rpc({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                    "params": {"name": "no_such_tool", "arguments": {}}})
ok = status == "OK" and "error" in json.loads(line)
report("nonexistent tool -> error", ok, line.strip()[:160] if line else status)

# ---- 4c. malformed params (wrong types) ----
status, line = rpc({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                    "params": {"name": "live_ping", "arguments": {"timeout": "not-a-number"}}})
ok = status == "OK" and "error" in json.loads(line)
report("wrong-typed argument -> error", ok, line.strip()[:200] if line else status)

# ---- 4d. params as wrong shape entirely ----
status, line = rpc({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": "garbage-string"})
ok = status == "OK" and "error" in json.loads(line)
report("params as string -> error", ok, line.strip()[:160] if line else status)

# ---- 4e. server still alive: tools/list again ----
status, line = rpc({"jsonrpc": "2.0", "id": 8, "method": "tools/list"})
ok = status == "OK" and len(json.loads(line)["result"]["tools"]) == len(tools)
report("server alive after garbage (tools/list again)", ok, status)

# ---- 4f. malformed JSON line (not JSON at all) ----
send_raw("this is not json {{{")
status, line = recv(timeout=3)
if status == "EOF":
    report("malformed JSON line", False, "SERVER DIED (stdout EOF) -- json.loads uncaught in serve()")
    proc.wait(timeout=5)
    print("exit code:", proc.returncode, flush=True)
    print("stderr tail:", err_lines[-15:], flush=True)
else:
    detail = line.strip()[:160] if line else "no response (line ignored?)"
    # verify still alive
    status2, line2 = rpc({"jsonrpc": "2.0", "id": 9, "method": "tools/list"})
    alive = status2 == "OK"
    report("malformed JSON line handled, server alive", alive, f"first reaction: {status}/{detail}")

if proc.poll() is None:
    proc.stdin.close()
    try:
        proc.wait(timeout=5)
        report("clean shutdown on stdin close", True, f"exit={proc.returncode}")
    except subprocess.TimeoutExpired:
        proc.kill()
        report("clean shutdown on stdin close", False, "had to kill after stdin close")

print("\nSTDERR (full):", flush=True)
for l in err_lines:
    print("  " + l, flush=True)

fails = [f for f in findings if not f["ok"]]
print(f"\nSUMMARY: {len(findings)-len(fails)}/{len(findings)} checks passed", flush=True)
