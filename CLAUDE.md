Read AGENTS.md

# Kim's fork — project context (local; never include this file or docs/PROGRESS.md in upstream pull requests)

**What this is:** Kim's fork of `bschoepke/ableton-live-mcp` — an MCP (Model Context Protocol) bridge that lets Claude Code control Ableton Live. Kim's role: Windows maintainer/contributor; the author only tests on macOS.

**Read next:** `docs/PROGRESS.md` — session-by-session status, findings backlog, and open pull requests.

## Branch policy
- `kim/main` — THIS branch: integration of all fixes + Kim's docs. The local checkout stays here so the registered MCP server runs fixed code.
- `fix/*` — one branch per upstream pull request, always cut from `upstream/main`, never containing CLAUDE.md/PROGRESS.md changes.
- `upstream` = bschoepke's repo (pull from), `origin` = AxidentDK fork (push to). Pushing this fork is authorized; opening upstream pull requests follows the agreed plan in PROGRESS.md.

## Commands
- Tests: `uv run --extra dev pytest -q` (expect 287/287 on kim/main)
- Validate against running Live: `uv run ableton-live-mcp-validate` (needs `runtime_current: true` + `live_mutations_safe: true`)
- Smoke (needs Live running): `$env:ABLETON_LIVE_MCP_DEBUG = "1"; uv run python src/smoke.py`
- Install remote script (plain, no env override needed on this machine): `uv run ableton-live-mcp-install-remote-script`

## Machine facts (Kim's PC)
- Ableton Live 12 Suite, install at `C:\ProgramData\Ableton\Live 12 Suite`; User Library is the STANDARD `C:\Users\Kim\Documents\Ableton\User Library` (a Library.cfg `ProjectPath` misread once suggested otherwise — it's the parent folder, don't repeat that detour).
- Remote script loads from `User Library\Remote Scripts\Ableton_Live_MCP`; control surface slot 2 = "Ableton Live MCP" (slot 1 = Komplete Kontrol S Mk3 — don't touch). Persists across restarts.
- MCP server registered user-scope in Claude Code as `ableton-live` → runs THIS checkout (`uv run --directory ...`), so whatever branch is checked out here is what Claude Code runs.
- Bridge = TCP on 127.0.0.1:8765, only alive while Live runs with the control surface enabled. Ref paths are Max/LOM-style space-separated (`live_set tracks 4 clip_slots 0 clip`), no negative indices.
- Restarting/closing Live is pre-authorized; match processes by `Name -like 'Ableton*'` only, never by window title.
