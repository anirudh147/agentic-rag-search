"""
Exports the live FastAPI app's OpenAPI schema to doc/api/openapi.json (and a
.yaml copy), so the Swagger/OpenAPI deliverable is a static, reviewable file
in the repo rather than only available while the server is running.

Run from the backend/ directory (needs the backend's deps installed):
    cd backend && python ../scripts/export_openapi.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import yaml  # noqa: E402

from app.main import app  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "doc", "api")
os.makedirs(OUT_DIR, exist_ok=True)

schema = app.openapi()

json_path = os.path.join(OUT_DIR, "openapi.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)
print(f"wrote {json_path}")

yaml_path = os.path.join(OUT_DIR, "openapi.yaml")
with open(yaml_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(schema, f, sort_keys=False)
print(f"wrote {yaml_path}")
