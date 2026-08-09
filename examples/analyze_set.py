"""Pull MIDI notes from the open Live set and print a musical summary."""
from collections import Counter
from live import rpc

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def pname(p):
    return f"{NAMES[p % 12]}{p // 12 - 2}"  # Ableton: C3 = 60


CLIPS = [
    ("Hype Bass", "live_set tracks 0 arrangement_clips 0"),
    ("Vital Monotome", "live_set tracks 1 arrangement_clips 0"),
    ("Vital Chords", "live_set tracks 2 arrangement_clips 0"),
    ("Vital Noise", "live_set tracks 3 arrangement_clips 0"),
    ("Wire Bass Journey", "live_set tracks 5 arrangement_clips 0"),
]

def all_notes(path, span=192, window=24):
    notes = []
    t = 0
    while t < span:
        r = rpc("clip_notes", {"ref": {"path": path}, "limit": 2000,
                               "start_time": t, "end_time": t + window})
        notes.extend(n for n in r["notes"] if "pitch" in n)
        t += window
    return notes


for label, path in CLIPS:
    notes = all_notes(path)
    print(f"\n=== {label} — {len(notes)} notes ===")
    if not notes:
        continue
    pcs = Counter(NAMES[n["pitch"] % 12] for n in notes)
    lo = min(n["pitch"] for n in notes)
    hi = max(n["pitch"] for n in notes)
    span = max(n["start_time"] + n["duration"] for n in notes)
    print(f"range {pname(lo)}..{pname(hi)}, spans {span:.1f} beats")
    print("pitch classes:", dict(pcs.most_common()))
    # first 2 bars in detail
    head = sorted([n for n in notes if n["start_time"] < 8], key=lambda n: (n["start_time"], n["pitch"]))
    for n in head[:40]:
        print(f"  t={n['start_time']:6.2f} dur={n['duration']:5.2f} {pname(n['pitch']):>4} vel={n['velocity']:.0f}")
