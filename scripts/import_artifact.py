"""Import the owner's Claude design artifact (the console SSOT) into `ui/console/`.

python scripts/import_artifact.py ARTIFACT.html [--out ui/console]

The artifact is a single-file build: one inline module script, one inline stylesheet and an
inline `window.__QC_DATA__`. We split the script and stylesheet into files, drop the inline
data so the bundle falls back to fetching `./data/...` (served live by `api.py`), and write
the derived-only `field`/`frontier`/`index` JSON with every SEM image removed (rule 9d).
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_LOOK = "polymer"


def _strip_images(field: dict[str, Any]) -> dict[str, Any]:
    # Reason: assets hold the base64 SEM tiles; with none, the bundle hides the image section.
    return {**field, "assets": {}}


def split_artifact(html: str) -> tuple[str, str, dict[str, Any]]:
    """Return (module script, stylesheet, inline data) from the artifact's HTML."""
    js = re.search(r'<script type="module" crossorigin>(.*?)</script>', html, re.S)
    css = re.search(r'<style rel="stylesheet" crossorigin>(.*?)</style>', html, re.S)
    data = re.search(r"<script>window\.__QC_DATA__=(.*?);?</script>", html, re.S)
    if not (js and css and data):
        raise ValueError("artifact layout changed: script, style or __QC_DATA__ not found")
    script = js.group(1)
    # Reason: the owner's default look is `console`; production defaults to Polymer.
    default = "return`console`}"
    if script.count(default) != 1:
        raise ValueError("default-look literal not found exactly once")
    script = script.replace(default, f"return`{DEFAULT_LOOK}`}}")
    return script, css.group(1), json.loads(data.group(1))


SHELL = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Polaron QC Console</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts}
<meta name="theme-color" content="#0E0F10">
<link rel="stylesheet" href="assets/app.css">
<script type="module" src="assets/app.js"></script>
</head>
<body>
<div id="root"></div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--out", type=Path, default=Path("ui/console"))
    args = parser.parse_args()
    html = args.artifact.read_text()
    script, css, data = split_artifact(html)
    fonts = re.search(r'<link href="https://fonts\.googleapis\.com/css2[^"]*"[^>]*>', html)
    out: Path = args.out
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "app.js").write_text(script)
    (out / "assets" / "app.css").write_text(css)
    (out / "index.html").write_text(SHELL.format(fonts=fonts.group(0) if fonts else ""))
    index = data["index"]
    for b in index["batches"]:
        b["imagery"] = False
    _write(out / "data" / "index.json", index)
    _write(out / "data" / "frontier.json", data.get("frontier"))
    for batch, entry in data["batches"].items():
        _write(out / "data" / batch / "field.json", _strip_images(entry["field"]))


def _write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, separators=(",", ":"))
    if "data:image" in text:
        raise ValueError(f"{path}: image data left in derived output")
    path.write_text(text)


if __name__ == "__main__":
    main()
