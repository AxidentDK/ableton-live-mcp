import json, re, sys
from pathlib import Path

SCRATCH = Path(r"C:\Users\Kim\AppData\Local\Temp\claude\C--Users-Kim\6822e0ee-25c2-403e-90fa-c879dc630175\scratchpad")
FAIL = []

def check(label, cond, detail=""):
    print("%-4s %s %s" % ("OK" if cond else "FAIL", label, detail))
    if not cond:
        FAIL.append(label)

def parse_container(path, expect_type):
    data = path.read_bytes()
    check("%s exists" % path.name, path.is_file(), "%d bytes" % len(data))
    # header: 'ampf' + u32le(4) + 4-byte type code + then chunks (tag + u32le len + payload)
    magic = b"ampf" + (4).to_bytes(4, "little") + expect_type + b"meta"
    check("%s magic prefix" % path.name, data.startswith(magic), repr(data[:16]))
    pos = 12  # after ampf/len/type
    chunks = []
    while pos + 8 <= len(data):
        tag = data[pos:pos+4]
        size = int.from_bytes(data[pos+4:pos+8], "little")
        payload = data[pos+8:pos+8+size]
        chunks.append((tag, size, len(payload)))
        pos += 8 + size
    check("%s chunk walk consumes file exactly" % path.name, pos == len(data),
          "end=%d filesize=%d chunks=%s" % (pos, len(data), [(t.decode('latin1'), s) for t, s, _ in chunks]))
    for tag, size, got in chunks:
        check("%s chunk %s length field intact" % (path.name, tag.decode('latin1')), size == got,
              "declared=%d available=%d" % (size, got))
    ptch = [c for c in chunks if c[0] == b"ptch"]
    check("%s has exactly one ptch chunk" % path.name, len(ptch) == 1)
    # extract ptch payload
    idx = data.find(b"ptch")
    size = int.from_bytes(data[idx+4:idx+8], "little")
    payload = data[idx+8:idx+8+size]
    check("%s ptch NUL-terminated" % path.name, payload.endswith(b"\x00"), repr(payload[-4:]))
    try:
        patch = json.loads(payload.rstrip(b"\x00").decode("utf-8"))
        check("%s ptch JSON parses" % path.name, True)
    except Exception as e:
        check("%s ptch JSON parses" % path.name, False, str(e))
        return None
    return patch

def scan_box_texts(name, patch):
    boxes = patch.get("patcher", {}).get("boxes", [])
    check("%s has boxes" % name, len(boxes) > 0, "%d boxes" % len(boxes))
    bad = []
    interesting = []
    for item in boxes:
        box = item.get("box", {})
        text = box.get("text")
        if text is None:
            continue
        if "\\" in text:
            bad.append((box.get("id"), text))
        if re.match(r"^(js |filewatch |udpreceive )", text) or text.startswith('"'):
            interesting.append((box.get("id"), text))
    check("%s no backslash in any box text" % name, not bad, str(bad)[:400])
    for bid, text in interesting:
        print("     box[%s]: %s" % (bid, text))
    # message boxes holding the command-file path
    for item in boxes:
        box = item.get("box", {})
        if box.get("id") == "command-filewatch-path":
            t = box.get("text", "")
            check("%s filewatch path quoted (space in state dir)" % name,
                  t.startswith('"') and t.endswith('"') and "/" in t and "\\" not in t, t)
    return boxes

print("=== AgentAudioTap.amxd ===")
tap = parse_container(SCRATCH / "out" / "AgentAudioTap.amxd", b"aaaa")
if tap:
    boxes = tap["patcher"]["boxes"]
    js_boxes = [b["box"]["text"] for b in boxes if b.get("box", {}).get("text", "").startswith("js agent_audio_tap.js")]
    check("AgentAudioTap js box rewritten with command file", len(js_boxes) >= 1 and all("agent_audio_tap_command.json" in t for t in js_boxes), str(js_boxes))
    for t in js_boxes:
        check("AgentAudioTap js arg forward slashes + quoted", '"' in t and "/" in t and "\\" not in t, t)
    bad = [(b["box"].get("id"), b["box"]["text"]) for b in boxes if "\\" in b.get("box", {}).get("text", "")]
    check("AgentAudioTap no backslash in any box text", not bad, str(bad)[:400])
    check("AgentAudioTap companion js copied", (SCRATCH / "out" / "agent_audio_tap.js").is_file())

print()
print("=== AgentM4L_instrument_Test_Lead.amxd (real Live 12 template wrapper) ===")
dev = parse_container(SCRATCH / "gen" / "AgentM4L_instrument_Test_Lead.amxd", b"iiii")
if dev:
    scan_box_texts("amxd-ptch", dev)
    check("amxd amxdtype is instrument", dev["patcher"].get("amxdtype") == 1768515945, str(dev["patcher"].get("amxdtype")))

print()
print("=== AgentM4L_instrument_Test_Lead.maxpat ===")
mp = json.loads((SCRATCH / "gen" / "AgentM4L_instrument_Test_Lead.maxpat").read_text(encoding="utf-8"))
boxes = scan_box_texts("maxpat", mp)
udp = [b["box"]["text"] for b in boxes if b.get("box", {}).get("text", "").startswith("udpreceive")]
port = int(udp[0].split()[1])
check("udp port in valid range", 17655 <= port < 17655 + 30000, str(port))
check("maxpat identical to embedded ptch", json.dumps(mp, sort_keys=True) == json.dumps(dev, sort_keys=True))
check("companion host js copied", (SCRATCH / "gen" / "agent_m4l_host.js").is_file())

print()
print("=== webui assets ===")
w = SCRATCH / "gen" / "webui" / "test_lead_01"
for f in ("index.html", "style.css", "device.js", "lib/three_sub/module.js"):
    check("webui %s written" % f, (w / f).is_file())
html = (w / "index.html").read_text(encoding="utf-8")
check("webui bootstrap injected", "agent-m4l-bootstrap" in html)
check("webui html no backslash paths", "\\" not in html.replace("\\n", ""), "")

print()
print("=== literal-backslash grep across generated artifacts ===")
for p in [SCRATCH / "out" / "AgentAudioTap.amxd",
          SCRATCH / "gen" / "AgentM4L_instrument_Test_Lead.amxd",
          SCRATCH / "gen" / "AgentM4L_instrument_Test_Lead.maxpat"]:
    raw = p.read_bytes()
    n = raw.count(b"\\")
    # In JSON, a legit escaped quote is \" — anything else path-like is a leak.
    suspicious = [m.start() for m in re.finditer(rb"\\(?![\"\\/bfnrtu])", raw)]
    check("%s backslash audit" % p.name, not suspicious,
          "total=%d suspicious=%d %s" % (n, len(suspicious),
          [raw[max(0,i-30):i+30] for i in suspicious[:3]]))

print()
print("RESULT:", "ALL PASS" if not FAIL else "FAILURES: %s" % FAIL)
sys.exit(1 if FAIL else 0)
