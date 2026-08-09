import json, os
import ableton_paths as ap

out = {
    "user_library_candidates": [str(p) for p in ap.user_library_candidates()],
    "default_user_library": str(ap.default_user_library()),
    "default_user_library_exists": ap.default_user_library().exists(),
    "remote_scripts_dir": str(ap.remote_scripts_dir()),
    "remote_scripts_dir_exists": ap.remote_scripts_dir().exists(),
    "live_install_roots": [str(p) + (" [exists]" if p.exists() else " [missing]") for p in ap._live_install_roots()],
    "live_install_candidates": [str(p) for p in ap._live_install_candidates()],
    "max_device_template_dirs_existing": [str(p) for p in ap.max_device_template_dirs() if p.exists()],
    "blank_templates_found": {
        name: (str(ap.find_max_device_template(name)) if ap.find_max_device_template(name) else None)
        for name in ("Max Audio Effect.amxd", "Max Instrument.amxd", "Max MIDI Effect.amxd")
    },
}
print(json.dumps(out, indent=2))
