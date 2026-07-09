#!/usr/bin/env python3
"""Patch androiddeployqt deployment settings JSON to add android-package-source-directory."""
import json, sys, os

json_path = sys.argv[1]
src_dir = sys.argv[2]

if not os.path.exists(json_path):
    print(f"[patch-deploy] JSON not found: {json_path}, skipping")
    sys.exit(0)

with open(json_path) as f:
    data = json.load(f)

key = "android-package-source-directory"
if data.get(key) != src_dir:
    data[key] = src_dir
    with open(json_path, "w") as f:
        json.dump(data, f, indent=3)
    print(f"[patch-deploy] Set {key} = {src_dir}")
else:
    print(f"[patch-deploy] Already up to date")
