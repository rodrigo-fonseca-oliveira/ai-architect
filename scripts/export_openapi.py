import json
from pathlib import Path

from app.main import app

if __name__ == "__main__":
    # Generate and save OpenAPI spec to docs/openapi.yaml in YAML (fallback to JSON if PyYAML missing)
    spec = app.openapi()
    out = Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml"
    try:
        import yaml  # type: ignore

        text = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
        out.write_text(text)
        print(f"Exported OpenAPI schema (YAML) to {out}")
    except Exception:
        # Minimal fallback to avoid blocking local runs without PyYAML
        out.write_text(json.dumps(spec, indent=2))
        print(f"Exported OpenAPI schema (JSON fallback) to {out}")
