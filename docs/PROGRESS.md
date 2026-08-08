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

New from the 2026-08-08 live music session (first real-world use, all confirmed against Live 12.4.3):
8. **AgentAudioTap goes deaf after Live's "Collect All and Save"** — existing instance stops creating files on `open`/`start` (UDP delivered, `sent:true`, no file ever appears). Workaround: delete the device from Main + rerun `live_agent_audio_tap_setup`. Suspect collect-and-save re-homes the device to the project's collected copy, killing the js `Task`/`udpreceive`. Fix candidate: setup (or the tap tool) should do a status round-trip and auto-reload a dead instance instead of trusting `devices:["AgentAudioTap"]`.
9. **Fresh tap instance records pure zeros if started too soon after load** — recorded a valid-size all-silence wav while `master_track.output_meter_level` showed ~0.86 signal. Waiting ~8 s between setup and `start` fixed it. Fix candidate: js `loadbang` should emit a ready status and setup should block on it rather than returning immediately.
10. **`live_transport` `play {time}` response reports the pre-seek time** — observed `play time=88` → `"time":164.8` and `play time=0` → status 139.5 moments later; seek-while-playing reliability unclear. Workaround: `live_exec` stop → `current_song_time = x` → `start_playing()`. Fix candidate: `_rpc_transport` re-reads time after `_seek_song` (settle), or seeks via stop/set/start when playing.
11. **`clip_notes` appends `{"truncated": true, "omitted": N}` INSIDE the notes array** (cap ~200/response) — every client must special-case a non-note dict in a notes list, and the info duplicates the top-level `truncated` flag. Move the marker to the top level.
12. Agent-guidance gap: tap captures happily record past the arrangement end (transport keeps running into silent timeline — burned two captures on this). Tap status or setup could expose song length / last-clip end so agents can bound captures.

## 2026-08-08 (late) — tap liveness handshake shipped (backlog #8/#9 closed)
- AgentAudioTap js now writes a status file (sibling of the baked command file: `state_dir()/agent_audio_tap_status.json`) on loadbang + every command, echoing `last_command_id` + `seq`. `live_agent_audio_tap_setup` handshakes (probe → poll for the id), auto-reloads a deaf instance with `remove_existing`, and returns `ready`/`reloaded`/`handshake`; `verify:false` opts out. 321/321 green.
- In-Live verified: fresh instance answered probe (status file id match, seq 2 after the loadbang event); capped 3 s capture of the running sketch finalized at −14.2 dBFS peak. NOTE for agents: setup's `stop` default halts the transport — the same-tick `playing` read in its result is stale (returned true after stopping); restart playback before capturing.
- The session MCP server exe runs pre-handshake code until next Claude Code restart; bridge + device are current now. Remaining: PR Lyle their stale tap-js test fix; consider upstreaming the whole set once #14/#15 move.

## 2026-08-08 (evening) — integrated lylepmills fixes, verified in-Live
- Checked all 8 upstream forks for existing fixes (Kim's idea; the forks page hides no-change forks — API shows all): only `lylepmills` (Rubato Audio, maintained fork) is ahead. Cherry-picked their 4 core commits (order matters: 8dbe132 → cb0129b → 380204b → 2f8e59d): deterministic tap stop (duration_ms/bars; sfrecord~ "record <ms>" does NOT self-terminate in Live 12.4), play_from/play_loop deferred-jump transport (root cause of our backlog #10: jump_by only works while transport genuinely running), record_track_to_wav turnkey, bounded retries. Kept our compact tool descriptions; dropped their macOS-only blank-capture recovery; took opt-in OCR (Windows stub). Their stale tap-js build test rewritten (broken on their branch too — PR them that).
- Fixed backlog #11 ourselves: clip_notes now raises the encoder max_items to its own limit (no more marker dict inside the notes array). Regression test added. 316/316 green.
- Deployed: remote script (`--force`) + rebuilt AgentAudioTap → restarted Live → runtime `transport-play-from-1` confirmed. In-Live verification: play_from landed at target (+elapsed) ✓; duration-capped tap self-stopped and finalized (3.02 s file, no stop sent) ✓.
- Gotcha: `Get-Process Name -like 'Ableton*'` now ALSO matches our own `ableton-live-mcp` server exe — check MainWindowTitle/path before concluding Live is still running. Also: uv can't sync the venv while the MCP server runs from it (exe locked) — use `uv run --no-sync`.
- Still open from the field list: #8 (tap deaf after Collect All and Save — needs js ready/status handshake in setup), #9 partially mitigated by the init-grace habit, #12 docs.

## 2026-08-08 — first real-world music session (menu loop for Unforeseen Consequences)
- Full production session driven over the bridge against Kim's live set: `set_summary`/`clip_notes` analysis, `clip_add_notes` (628-note payload in one call — fine), `clip_duplicate_to_arrangement`, `browser_search`/`browser_load` incl. **VST loading via roots:['plugins']** (Arturia ARP 2600 V3), `clip_envelope` automation (Auto Filter sweep), `device_parameters`/`parameter_set` on stock + VST devices, AgentAudioTap master captures + offline BS.1770 LUFS measurement. Everything worked on Windows except the new backlog items 8–12 above.
- Also proven: offline-sample rescue workflow (read .als gzip XML for original paths → relative `../` relink trick), and the tap→numpy analysis loop (K-weighted LUFS, vibrato measurement at ±11 cents / 1.84 Hz).

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

## 2026-08-08 (later)
- New standing rule: write topic .md files the moment important info surfaces. First one: docs/WINDOWS-VALIDATION.md — full detail behind the findings backlog (file:line, repro, clean areas, live-bridge usage recipes).
