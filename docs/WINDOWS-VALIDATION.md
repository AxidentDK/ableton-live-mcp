# Windows validation details — 2026-08-07 five-agent sweep

Full detail behind the backlog in PROGRESS.md, so nothing is lost if session context goes away. Environment: Windows 11 Pro, Python 3.14.3, uv 0.11.8, Ableton Live 12 Suite 12.4.3, `windows-capture` 2.0.0 (cp39-abi3 wheel, so 3.14-compatible), Pillow 12.3.0.

## MCP stdio server (verified by driving the real process over pipes)
- Handshake 0.21 s; 37 tools; `tools/list` response 17,405 bytes (~4.3k tokens); largest tool def `live_clip_add_notes` (1,132 bytes).
- Without Live: `live_ping {"timeout": 2}` → clean `-32000` in 4.03 s. The 4 s = `connect_timeout` 2.0 s default (`src/bridge.py:31`) × one retry on OSError (`src/bridge.py:73-77`); on Windows a closed localhost port SYN-retries instead of refusing instantly, so it reads "timed out" not "refused". Tune with `ABLETON_MCP_CONNECT_TIMEOUT`.
- Graceful: unknown method, unknown tool, wrong-typed arg (own mini validator: "arguments.timeout must be number"). Rough edge: `params` as a string leaks `'str' object has no attribute 'get'`.
- **Crash (fixed in PR #15)**: non-JSON stdin line → `json.loads` outside try in `serve()` (`src/mcp_stdio.py:57` pre-fix) → process death, exit 1. Reproduced live with `this is not json {{{`.
- **cp1252 (fixed in PR #15)**: piped stdio inherited cp1252; UTF-8 `å` arrived as `Ã¥`; Cyrillic `с` → lone surrogate emitted as invalid `\udc81` JSON escape. Output side was ASCII-safe only because `json.dumps` defaults to `ensure_ascii=True`; input side corrupted silently. Response frames ended `\r\n`.
- `src/smoke.py` without Live: degrades cleanly, 13 checks `ok:false`, exit 1, `browser_plugin_search` intentionally soft.

## Visual capture (proven with real pixel captures)
- `windows-capture` selects by HWND (`src/visual_capture.py:566-568` prefers `window_hwnd` param). Enumeration via ctypes `EnumWindows`/`GetWindowTextW`/`QueryFullProcessImageNameW` — accurate (7/7 windows, correct PIDs/bounds).
- Proof captures: 2560×1392 non-blank (module's own detector: mean_luma 23.3, nonblack_fraction 1.0), crop `100,100,1200,800` + max_width 400 → correct 400×267; region `device-detail` bottom_fraction 0.25 → correct strip.
- Safety guard works: non-Ableton window → clean `RuntimeError` (`visual_capture.py:590-604`).
- Bugs: `--max-console --list` exits 1 despite success (`main` returns `0 if result.get("ok")` at `visual_capture.py:905`; list results have no `ok` key; plain `--list` unaffected, line 922). Windows `--max-console --list` always attempts `list_macos_displays()` → confusing `displays_error` (`visual_capture.py:180-183`). `--display <n>` fallback macOS-only (`visual_capture.py:282-284`) though the library supports `monitor_index`.

## M4L builders (byte-level container verification)
- `.amxd` walk: `ampf` + u32le(4) + `aaaa`/`iiii` + `meta`(len 4) + `ptch`(len little-endian) consumes files byte-exactly; ptch payload NUL-terminated valid JSON identical to sibling `.maxpat`. Chunk surgery: `replace_ptch_chunk` (`src/agent_m4l.py:201-219`) correct.
- Instrument build used the real template `C:\ProgramData\Ableton\Live 12 Suite\Resources\Misc\Max Devices\Max Instrument.amxd` (`amxdtype` 1768515945) via ProgramData scan (`src/ableton_paths.py:106-109`).
- Zero backslash leaks even with a state dir containing a space (quoted forward-slash paths via `max_arg`, `src/agent_m4l.py:176-180`); `udpreceive` port in valid range [17655, 47655).
- `ableton-live-mcp-sync-m4l-host --dry-run`: found User Library, both targets current (SHA-256 match), 0/3 stale wrappers. Wet run copies into repo + User Library and rewrites installed `.amxd` wrappers in place (`src/agent_m4l.py:657-688`).
- Footgun: `build_device`/`write_webui` hard-code output to `<repo>/m4l/generated` (`GENERATED_DIR`, `src/agent_m4l.py:16,460-461`), no output flag.

## Environment / paths
- `similar_sounds` Windows branch reads `%LOCALAPPDATA%\Ableton\Live Database\Live-files-*.db` (`src/similar_sounds.py:31-36`), sqlite3 `mode=ro` URI works with backslashes+spaces; verified query "kick" → `Kick 02 - E.aif` base, neighbors at distances 3.05/3.59/3.75.
- `ableton_paths` caveats: `Live*` glob false-positive on `%LOCALAPPDATA%\Ableton\Live Database` (`src/ableton_paths.py:120`, benign); `Path.home()/"Documents"` misses OneDrive Known-Folder redirection (`src/ableton_paths.py:39`, not the case on this machine).
- **Library.cfg trap**: `<LibraryProject ProjectPath>` is the PARENT of the User Library project, not the library root. Misreading it cost a detour on 2026-08-07. The UI (Settings → Library) is authoritative: standard `Documents\Ableton\User Library` here. Live loads the remote script from `User Library\Remote Scripts\Ableton_Live_MCP`; `Documents\Ableton\Remote Scripts` is NOT scanned (no `__pycache__` ever appeared there).
- Ports: bridge 8765, AgentAudioTap UDP 17654, agent-M4L UDP base 17655 (+span 30000).

## Windows audit remainder (not yet fixed/filed — details for future PRs)
- **AgentAudioTap DOA**: shipped `.amxd` embeds `js agent_audio_tap.js /Users/ben/.ableton-live-mcp/agent_audio_tap_command.json`; shipped `.maxpat` has no path arg so `m4l/agent_audio_tap.js:7` falls back to a relative path; Remote Script writes commands to `%USERPROFILE%\.ableton-live-mcp\` (`Ableton_Live_MCP/bridge.py:425-430`); UDP wake default False (`bridge.py:433`) → silent no-op. Fix locally: `scripts/build_agent_audio_tap.py --install` (its own `max_arg` normalizes).
- Embedded bridge `open()` without `encoding=` at `Ableton_Live_MCP/bridge.py:426, 544, 778, 795, 807` (latent: both sides ASCII today via `ensure_ascii=True`; server side reads UTF-8 explicitly at `src/server.py:1149,1169,1350`).
- `src/validate.py:127` probe reads `bridge.py` without `encoding=` — fingerprint would diverge if non-ASCII ever lands in that file.
- `SO_REUSEADDR` on Windows = hijack semantics (`Ableton_Live_MCP/bridge.py:139`); `SO_EXCLUSIVEADDRUSE` is the Windows-correct flag. Low risk (loopback).
- State-dir split: `ABLETON_MCP_STATE_DIR` set only in the MCP client env is invisible to Live launched from Explorer → command/status files diverge (`Ableton_Live_MCP/bridge.py:97`).
- Watch item: `write_webui()` passes raw backslash `html_path` to jweb `readfile` (`src/agent_m4l.py:713-717` → `m4l/agent_m4l_host.js:886-894`); retry series falls back to `file:///` URL (`agent_m4l_host.js:1277-1282`) so probably self-heals; verify once live.
- AGENTS.md POSIX-only commands at lines 81 (`.venv/bin/python`) and 198 (`VAR=1` prefix).
- Clean areas (audited, no issues): embedded bridge Python 3.7/3.11 compat (no f-strings/match/walrus, pure ASCII, no /tmp/fork/signal), `src/bridge.py` socket client, `install_remote_script.py`, m4l JS files (no POSIX paths, no `say`, no drive-letter splitting), pyproject platform markers.

## Live-bridge usage notes (learned the hard way)
- Ref paths are Max/LOM-style space-separated: `live_set tracks 4 clip_slots 0 clip` (`_resolve_path` splits on whitespace; roots: `live_set|song|app|browser|this`; integer tokens index into the preceding collection; **no negative indices**).
- RPC method names = MCP tool names minus `live_` prefix (`live_exec` → `exec`, etc.); `exec` env exposes `Live`, `song`, `app`, `obj`, `this`, `result`.
- TCP bridge is UTF-8-clean end-to-end (åäö round-tripped byte-perfect on 2026-08-07); only the stdio layer had the encoding bug.
- E2E recipe that works: create track via `exec` (`song.create_midi_track(-1)`), clip via `clip_slots[0].create_clip(4.0)`, notes via `clip_add_notes` RPC with `{pitch,start_time,duration,velocity}`, read back via `clip_notes`, delete via `song.delete_track(index)`.
