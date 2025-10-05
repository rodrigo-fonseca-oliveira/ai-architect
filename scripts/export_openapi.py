import json
from pathlib import Path

from app.main import app

if __name__ == "__main__":
    # Generate and save OpenAPI spec to docs/openapi.yaml (JSON->YAML not required; keep JSON or convert if needed)
    spec = app.openapi()
    out = Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml"
    out.write_text(json.dumps(spec, indent=2))
    print(f"Exported OpenAPI schema to {out}")
