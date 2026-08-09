"""Drive agent_m4l:main (the ableton-live-mcp-build-m4l-device entry point)
with output dirs redirected to the scratchpad so nothing is written inside
the repo or the Ableton User Library."""
import sys
from pathlib import Path

SCRATCH = Path(r"C:\Users\Kim\AppData\Local\Temp\claude\C--Users-Kim\6822e0ee-25c2-403e-90fa-c879dc630175\scratchpad")

import agent_m4l

# Redirect repo-internal output dirs (module globals used by build_device/write_webui)
agent_m4l.GENERATED_DIR = SCRATCH / "gen"
agent_m4l.WEBUI_DIR = SCRATCH / "gen" / "webui"

# Exercise the real CLI: instrument role, name with a space, no install.
sys.argv = ["ableton-live-mcp-build-m4l-device", "--role", "instrument",
            "--name", "Test Lead", "--no-install", "test lead 01"]
agent_m4l.main()

# Also exercise webui asset materialization (write_webui) with a nested asset path
info = agent_m4l.write_webui("test lead 01", {
    "title": "Test Lead",
    "controls": [{"id": "cutoff", "label": "Cutoff", "min": 20, "max": 20000, "value": 800}],
    "assets": {"lib/three sub/module.js": {"content": "export const x = 1;\n"}},
})
import json
print(json.dumps(info, indent=2))

# Print resolved metadata for verification
res = agent_m4l.build_device.__wrapped__ if hasattr(agent_m4l.build_device, "__wrapped__") else None
print("command_file:", agent_m4l.command_file("test lead 01"))
print("status_file:", agent_m4l.status_file("test lead 01"))
print("udp_port:", agent_m4l.udp_port("test lead 01"))
print("template_used:", agent_m4l.role_template("instrument"))
