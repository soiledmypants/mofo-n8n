"""Targeted body re-rolls with per-slot fix notes.

    python tools/render_bodies.py --only chef,hazmat,puffer,spacesuit,tuxedo

Renders against refs/character.png (the arms-down master) ONLY — never the
eyes ref, which is what used to re-insert eye sockets. Each slot can carry an
extra clause aimed at the exact way it failed last time. Output goes straight
to traits/body/<name>.png for review BEFORE committing; nothing pushes itself.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from build_trait_workflow import BODIES, body_prompt  # noqa: E402

KEY_FILE = Path(r'C:\Users\rigby\AppData\Local\Temp\claude\C--Users-rigby\1a944995-7b70-4754-a07c-1191f7d8d97f\scratchpad\openai.key')

# Global hardening appended to every render: the drift is always toward dark.
BRIGHT = (
    " The entire image is brightly lit with rich, fully saturated colours - "
    "nothing is darkened, greyed out, or in shadow, and every clothing colour "
    "is vivid and true to its description."
)

# Per-slot notes aimed at each slot's last failure.
FIXES = {
    'chef': ' The chef jacket is PURE WHITE #FFFFFF fabric with black buttons - the jacket is white, not black, not grey.',
    'hazmat': ' The head is fully OPAQUE and filled solid with lavender-white #E8EAFB - never transparent, never dark, never showing the background through it.',
    'puffer': ' Both gloves are PURE SNOW-WHITE #FFFFFF like classic cartoon mascot gloves - absolutely not black.',
    'spacesuit': ' Every shape is FILLED with solid colour: the suit panels solid white #F2F2F6, the joints and trim solid colours - no empty, unfilled, or wireframe areas anywhere.',
    'tuxedo': '',
    'street': ' The sneakers are chunky and WHITE #FFFFFF with black outlines.',
}


def render(key: str, prompt: str) -> bytes:
    import mimetypes
    import uuid
    boundary = f"----mofo{uuid.uuid4().hex}"
    buf = bytearray()
    for k, v in {
        "model": "gpt-image-1", "prompt": prompt, "n": "1",
        "size": "1024x1024", "quality": "medium", "background": "transparent",
    }.items():
        buf += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    ref = ROOT / 'refs' / 'character.png'
    ctype = mimetypes.guess_type(ref.name)[0] or 'image/png'
    buf += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image[]\"; "
        f"filename=\"{ref.name}\"\r\nContent-Type: {ctype}\r\n\r\n"
    ).encode()
    buf += ref.read_bytes()
    buf += b"\r\n"
    buf += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/edits", data=bytes(buf),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=420) as r:
        payload = json.load(r)
    return base64.b64decode(payload["data"][0]["b64_json"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', required=True, help='comma-separated body names')
    args = ap.parse_args()

    key = KEY_FILE.read_text(encoding='utf-8').strip()
    names = [n.strip() for n in args.only.split(',') if n.strip()]
    out_dir = ROOT / 'traits' / 'body'
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in names:
        if name not in BODIES:
            print(f'  !! unknown body: {name}')
            continue
        prompt = body_prompt(BODIES[name]) + BRIGHT + FIXES.get(name, '')
        try:
            png = render(key, prompt)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors='replace')[:200]
            print(f'  {name}: HTTP {e.code} {body}')
            if e.code in (401, 403) or 'credit' in body or 'quota' in body:
                sys.exit('  stopping - key/credit problem')
            continue
        (out_dir / f'{name}.png').write_bytes(png)
        print(f'  {name}: rendered ({len(png)//1024} KB)')

    print('\n  review before committing - nothing pushed yet')


if __name__ == '__main__':
    main()
