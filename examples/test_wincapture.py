"""Prove the windows-capture backend produces real pixels on this machine.

Reuses ableton-live-mcp's visual_capture module functions where possible:
- list_platform_windows() for enumeration
- the exact WindowsCapture(window_hwnd=...) pattern from capture_windows_window
- postprocess_capture() for crop / downscale / blank detection
- also verifies capture_windows_window's non-Ableton refusal guard fires cleanly
"""
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Kim\source\repos\ableton-live-mcp\src")

from visual_capture import (
    list_platform_windows,
    capture_windows_window,
    postprocess_capture,
    window_area,
)

SCRATCH = Path(r"C:\Users\Kim\AppData\Local\Temp\claude\C--Users-Kim\6822e0ee-25c2-403e-90fa-c879dc630175\scratchpad")

windows = list_platform_windows()
# Pick a large real app window (skip shell/input hosts).
skip_owners = {"TextInputHost", "explorer", "ApplicationFrameHost", "RtkUWP"}
candidates = sorted(
    [w for w in windows if w.owner not in skip_owners and window_area(w) > 100000],
    key=window_area,
    reverse=True,
)
target = candidates[0]
print("target window:", target.title, "| owner:", target.owner, "| hwnd:", target.id, "| bounds:", target.bounds)

# 1) Verify the module's safety guard refuses a non-Ableton window cleanly.
try:
    capture_windows_window(target, SCRATCH / "should_not_exist.png")
    print("GUARD: FAILED - module captured a non-Ableton window!")
except RuntimeError as exc:
    print("GUARD OK (RuntimeError):", exc)

# 2) Capture using the exact same backend pattern as capture_windows_window
#    (visual_capture.py lines 552-587): hwnd selection, frame save, stop.
from windows_capture import InternalCaptureControl, WindowsCapture

out = SCRATCH / "backend_proof.png"
capture = WindowsCapture(cursor_capture=False, draw_border=False, monitor_index=None, window_hwnd=int(target.id))
saved = {"ok": False}

@capture.event
def on_frame_arrived(frame, capture_control: InternalCaptureControl):
    frame.save_as_image(str(out))
    saved["ok"] = True
    capture_control.stop()

@capture.event
def on_closed():
    return None

capture.start()
print("frame saved:", saved["ok"], "| file exists:", out.exists(), "| size:", out.stat().st_size if out.exists() else 0)

# 3) Run the module's own postprocess on the full capture (blank detection).
stats_full = postprocess_capture(out)
print("full postprocess:", stats_full)

# 4) Crop + downscale via the module's postprocess (same code the CLI uses).
import shutil
crop_out = SCRATCH / "backend_proof_crop_scaled.png"
shutil.copyfile(out, crop_out)
stats_crop = postprocess_capture(crop_out, crop="100,100,1200,800", max_width=400)
print("crop+downscale postprocess:", stats_crop)

# 5) Region 'device-detail' + bottom_fraction path too.
region_out = SCRATCH / "backend_proof_region.png"
shutil.copyfile(out, region_out)
stats_region = postprocess_capture(region_out, region="device-detail", bottom_fraction=0.25, max_height=300)
print("region postprocess:", stats_region)
