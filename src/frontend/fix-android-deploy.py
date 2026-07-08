#!/usr/bin/env python3
"""Post-configure script: patch androiddeployqt deployment settings
to include the custom Android package source directory."""
import json, sys, os

json_path = os.path.join(sys.argv[1], "android-appfrontend-deployment-settings.json")
android_src = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "android"
)

if not os.path.exists(json_path):
    print(f"[fix-android] Warning: {json_path} not found, skipping")
    sys.exit(0)

with open(json_path) as f:
    data = json.load(f)

key = "android-package-source-directory"
if data.get(key) != android_src:
    data[key] = android_src
    with open(json_path, "w") as f:
        json.dump(data, f, indent=3)
    print(f"[fix-android] Set {key} = {android_src}")
else:
    print(f"[fix-android] Already correct")
