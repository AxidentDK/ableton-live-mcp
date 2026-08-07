# Progress — Kim's fork of ableton-live-mcp

Newest entries first. Keep this updated after every significant step (same routine as APC/CubeSlide).

## Status snapshot (2026-08-08)
- Fork: `AxidentDK/ableton-live-mcp` · local: `C:\Users\Kim\source\repos\ableton-live-mcp` on branch `kim/main`
- Bridge fully working end-to-end on Kim's machine (Live 12.4.3, Windows 11, Python 3.14)
- Open upstream pull requests: [#14](https://github.com/bschoepke/ableton-live-mcp/pull/14) (Windows test fixes), [#15](https://github.com/bschoepke/ableton-live-mcp/pull/15) (UTF-8 stdio + parse resilience) — awaiting bschoepke's response (`gh pr view 14 --repo bschoepke/ableton-live-mcp`)
- Tests on `kim/main`: 287/287

## Findings backlog (from the 2026-08-07 five-agent Windows sweep)
Fixed and filed:
- ~~Tests compare raw backslash paths vs `max_arg()` forward-slash output~~ → PR #14
- ~~cp1252 stdio corrupts å/ä/ö; `\r\n` framing~~ → PR #15
- ~~Malformed stdin line kills the server (`mcp_stdio.py` serve loop)~~ → PR #15

Next candidates (not yet filed):
1. **AgentAudioTap.amxd ships broken for Windows**: `/Users/ben/...` command path baked into the checked-in device + UDP fallback off by default → silently never records. Workaround: `uv run python scripts/build_agent_audio_tap.py --install`. Upstream fix: stop shipping a machine-specific artifact, or rebuild in `live_agent_audio_tap_setup` on path mismatch.
2. Embedded bridge (`Ableton_Live_MCP/bridge.py`): 5× `open()` without `encoding="utf-8"` — latent asymmetry with the server side (which reads UTF-8 explicitly).
3. `--max-console --list` succeeds but exits 1 (`visual_capture.py:905`); same mode pointlessly attempts macOS display enumeration on Windows.
4. `src/mcp.py` is dead code (nothing imports it; near-duplicate of `mcp_stdio.py` with the old parse-crash bug; name would shadow the PyPI `mcp` package).
5. AGENTS.md gives POSIX-only commands (`.venv/bin/python`, `VAR=1 cmd`) despite claiming Windows support.
6. Cosmetics: `SO_REUSEADDR` hijack semantics on Windows (bridge port), macOS path unconditionally appended in `similar_sounds.py`, `Live*` glob false-positive on `Live Database`, OneDrive-redirected Documents would defeat User Library discovery.
7. Watch item: `write_webui()` passes a raw backslash `html_path` to jweb `readfile` — the one path bypassing `max_arg()`; probably self-heals via the `file:///` fallback; verify once with a live device.
- Known design caveats (not bugs): bridge socket has no auth (any local process can eval Python inside Live); generated M4L devices hard-coded to `m4l/generated/` inside the checkout.

## 2026-08-08
- Created `kim/main` integration branch (both fix branches merged) + this documentation. Local checkout and the registered MCP server now run all fixes.

## 2026-08-07 — evaluation → fork → full Windows validation → live bridge → 2 PRs (one session)
- **Evaluated** Ableton MCP bridges; picked `bschoepke/ableton-live-mcp` over ahujasid's (2.9k stars but stale PRs) — most capable architecture: ~40 tools + `live_eval`/`live_exec` (arbitrary Python inside Live), Agent Audio Tap M4L device, visual capture, 7.4k test lines incl. fake-Live harness, zero runtime deps, active owner. Openly AI-authored (Codex).
- **Forked** to AxidentDK, cloned with `upstream` remote. Found + fixed 2 Windows-only test failures (285/285) → later PR #14.
- **Five-agent wide sweep** validated every subsystem on Windows without Live running: MCP protocol layer (37 valid schemas, graceful degradation), environment/path detection (matches real install), visual capture (real pixels via windows-capture on Py 3.14), M4L builders (byte-valid .amxd, zero backslash leaks), plus a full platform-sensitivity audit → findings backlog above.
- **Live bridge brought up**: remote script installed + control surface selected (detour: misread Library.cfg as non-standard User Library; wrong — UI confirmed standard; redundant copy removed). Validator all green, smoke 13/13, E2E PASS: track/clip/notes round-trip incl. åäö (TCP path is UTF-8-clean; only stdio layer had the cp1252 bug).
- **Registered** the server user-scope in Claude Code (`ableton-live` entry in `~\.claude.json`) — future sessions get `live_*` tools natively.
- **Wrote + pushed** both fixes; opened PRs #14 and #15 upstream.
- Session lessons now encoded in CLAUDE.md (LOM path grammar, process-name matching, Library.cfg trap).
