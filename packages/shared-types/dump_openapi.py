"""Write the API's OpenAPI document to openapi.json (input for the TypeScript type generator)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "apps" / "api"))
from unboxed_api.main import app  # noqa: E402

(HERE / "openapi.json").write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print("wrote", HERE / "openapi.json")
