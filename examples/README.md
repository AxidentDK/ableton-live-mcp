# examples/

Ad-hoc client and dev scripts used while driving Live through the bridge. These
are **not** the packaged pytest suite (see `../tests/`) — they're the loose
usage/demo/dev scripts from the build sessions, collected here so they aren't
lost. Most import the tiny client below.

## The client

- **`live.py`** — minimal TCP JSON-lines client for the remote script on
  `127.0.0.1:8765`. Usage from any Python once Live is open with the remote
  script loaded:
  ```python
  from live import rpc
  print(rpc("ping"))
  notes = rpc("clip_notes", {"ref": {"path": "live_set tracks 0 clip_slots 0"}})
  ```

## Usage demos

- **`analyze_set.py`** — pull all MIDI notes from the open set and print a
  musical summary (pitches, chords, per-track).
- **`lufs.py`** — integrated LUFS (ITU-R BS.1770-4) of a WAV, numpy only:
  `python lufs.py render.wav`.

## Dev / smoke scripts

- **`e2e_bridge_test.py`** — end-to-end: create MIDI track + clip + notes via
  the bridge, verify, clean up.
- **`mcp_stdio_test.py`** — stdio round-trip against the MCP server, no Ableton
  required.
- **`test_wincapture.py`** — prove the Windows visual-capture backend returns
  real pixels on this machine.
- **`drive_build.py`** — drive the M4L device build with output dirs redirected
  out of the repo / User Library.
- **`probe_paths.py`** — probe `ableton_paths` resolution.
- **`verify_artifacts.py`** — sanity-check build artifacts.

> Compositions built with this client live with their tracks, not here — each
> Ableton project folder under `D:\Ableton Live projects\<name>\scripts\` carries
> its own copy of `live.py` plus the scripts that generated that track.
