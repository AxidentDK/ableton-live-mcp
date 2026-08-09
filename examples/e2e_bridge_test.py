"""End-to-end test: create MIDI track + clip + notes via the live bridge, verify, clean up."""
import json

from bridge import AbletonBridgeClient, BridgeConfig

TRACK_NAME = "MCP_E2E_TEST spår åäö"

client = AbletonBridgeClient(BridgeConfig.from_env())
results = {}

# 0. Remove any leftover test tracks from earlier runs
r = client.request("exec", {"code": (
    "removed = 0\n"
    "while True:\n"
    "    names = [t.name for t in song.tracks]\n"
    "    if %r not in names:\n"
    "        break\n"
    "    song.delete_track(names.index(%r))\n"
    "    removed += 1\n"
    "result = {'removed_leftovers': removed}"
) % (TRACK_NAME, TRACK_NAME)})
results["pre_cleanup"] = r

# 1. Create a MIDI track at the end and rename it (Swedish chars on purpose)
r = client.request("exec", {"code": (
    "before = len(song.tracks)\n"
    "song.create_midi_track(-1)\n"
    "track = song.tracks[before]\n"
    "track.name = %r\n"
    "result = {'before': before, 'after': len(song.tracks), 'name': track.name, 'index': before}"
) % TRACK_NAME})
results["create_track"] = r
assert r["after"] == r["before"] + 1, "track count did not increase"
assert r["name"] == TRACK_NAME, "track name mismatch: %r" % r["name"]
idx = r["index"]
clip_path = "live_set tracks %d clip_slots 0 clip" % idx

# 2. Create a 4-beat clip in slot 0
r = client.request("exec", {"code": (
    "track = song.tracks[%d]\n"
    "slot = track.clip_slots[0]\n"
    "slot.create_clip(4.0)\n"
    "clip = slot.clip\n"
    "clip.name = 'testklipp åäö'\n"
    "result = {'clip_name': clip.name, 'length': clip.length}"
) % idx})
results["create_clip"] = r
assert r["clip_name"] == "testklipp åäö", "clip name mismatch: %r" % r["clip_name"]

# 3. Add a C-major arpeggio via the dedicated notes RPC
notes = [
    {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100},
    {"pitch": 64, "start_time": 1.0, "duration": 0.5, "velocity": 90},
    {"pitch": 67, "start_time": 2.0, "duration": 0.5, "velocity": 90},
    {"pitch": 72, "start_time": 3.0, "duration": 0.5, "velocity": 110},
]
r = client.request("clip_add_notes", {"ref": {"path": clip_path}, "notes": notes})
results["add_notes"] = r

# 4. Read the notes back and verify
r = client.request("clip_notes", {"ref": {"path": clip_path}})
results["read_notes"] = r
got = r["notes"] if isinstance(r, dict) and "notes" in r else r
pitches = sorted(n["pitch"] for n in got)
assert pitches == [60, 64, 67, 72], "pitch mismatch: %r" % pitches

# 5. Clean up: delete the test track, verify count restored
r = client.request("exec", {"code": (
    "names = [t.name for t in song.tracks]\n"
    "idx = names.index(%r)\n"
    "song.delete_track(idx)\n"
    "result = {'deleted_index': idx, 'tracks_now': len(song.tracks), 'still_there': %r in [t.name for t in song.tracks]}"
) % (TRACK_NAME, TRACK_NAME)})
results["cleanup"] = r
assert not r["still_there"], "test track was not deleted"
assert r["tracks_now"] == results["create_track"]["before"], "track count not restored"

print(json.dumps(results, indent=2, ensure_ascii=False))
print("\nE2E PASS: track+clip created, 4 notes round-tripped, Swedish characters intact, cleanup verified.")
