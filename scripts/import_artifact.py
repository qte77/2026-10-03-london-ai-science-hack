"""Import the owner's Claude design artifact (the console SSOT) into `ui/console/`.

python scripts/import_artifact.py ARTIFACT.html [--out ui/console]

The artifact is a single-file build: one inline module script, one inline stylesheet and an
inline `window.__QC_DATA__`. We split the script and stylesheet into files, drop the inline
data so the bundle falls back to fetching `./data/...` (briefs served live by `api.py`), and
write the `field`/`frontier`/`index` JSON with each inline SEM tile saved as an image file next
to it (owner approved publishing the tiles, 2026-10-04).
"""

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_LOOK = "polymer"


def _extract_images(field: dict[str, Any], batch_dir: Path) -> dict[str, Any]:
    """Save each inline `data:` image as a file; the bundle prefixes `./data/<batch>/`."""
    for key, asset in (field.get("assets") or {}).items():
        for holder, name in ((asset, key), (asset.get("segmentation") or {}, f"{key}.seg")):
            uri = holder.get("image")
            if isinstance(uri, str) and uri.startswith("data:"):
                head, b64 = uri.split(",", 1)
                ext = head.removeprefix("data:image/").split(";")[0].replace("jpeg", "jpg")
                rel = f"img/{name}.{ext}"
                (batch_dir / "img").mkdir(parents=True, exist_ok=True)
                (batch_dir / rel).write_bytes(base64.b64decode(b64))
                holder["image"] = rel
    return field


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
    script = script.replace(default, f"return`{DEFAULT_LOOK}`}}", 1)
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
<link rel="stylesheet" href="assets/overrides.css">
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
    # Reason: owner wants the artifact served as-is (inline data + imaging bay), so the page is
    # the artifact's own HTML; only the Polymer default and our header overrides are added.
    page = html.replace("return`console`}", f"return`{DEFAULT_LOOK}`}}", 1).replace(
        '<div id="root"></div>',
        '<link rel="stylesheet" href="assets/overrides.css">\n<div id="root"></div>',
        1,
    )
    (out / "index.html").write_text(page)
    (out / "shell.html").write_text(SHELL.format(fonts=fonts.group(0) if fonts else ""))
    index = data["index"]
    _write(out / "data" / "index.json", index)
    _write(out / "data" / "frontier.json", data.get("frontier"))
    for batch, entry in data["batches"].items():
        batch_dir = out / "data" / batch
        _write(batch_dir / "field.json", _extract_images(entry["field"], batch_dir))


def _write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, separators=(",", ":"))
    if "data:image" in text:
        raise ValueError(f"{path}: inline image data left in JSON")
    path.write_text(text)


if __name__ == "__main__":
    main()
