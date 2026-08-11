"""
THE TRAIT MAPPER + COMPOSER: turn trait layers into a finished collection.

    python tools/compose_traits.py --count 333

Reads   traits/background/*.png   traits/outfit/*.png   traits/eyes/*.png
Writes  collection/0.png + 0.json ... N.png + N.json    (launchmynft-ready)
        collection/_trait-counts.csv                     (rarity table)

HOW THE MAPPING WORKS
  1. Every possible combo is enumerated: 10 x 10 x 10 = 1,000 triples.
  2. A seeded shuffle orders them; the first `count` are taken. Sampling
     without replacement means uniqueness is guaranteed by construction --
     no dedupe, no retries, and the same seed always yields the same set.
  3. Each token's sidecar records exactly which traits built it, and that
     same record becomes the marketplace `attributes` array. The metadata
     can't lie about the pixels, because the pixels were made FROM it.

HOW THE COMPOSITING SURVIVES AI WOBBLE
  gpt-image-1 doesn't place the character pixel-identically across renders,
  so raw layers would drift. Every outfit layer is therefore normalized:
  its opaque bounding box is scaled to a canonical height and planted on a
  fixed baseline, centered. Eyes are placed by detecting the lavender head
  blob in THAT outfit layer and scaling the eye art to the head that's
  actually there -- not to where a head is assumed to be.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from itertools import product
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TRAITS = ROOT / 'traits'

CANVAS = 1024
CHAR_HEIGHT = 880          # normalized character height, px
BASELINE = 984             # feet sit here after normalization
HEAD_RGB = (232, 234, 251) # #E8EAFB
HEAD_TOL = 46
EYES_WIDTH_FRAC = 0.80     # eye art width as fraction of detected head width
EYES_CY_FRAC = 0.46        # eye center as fraction of head height from its top


def load_dir(d: Path) -> dict[str, Image.Image]:
    out = {}
    for f in sorted(d.glob('*.png')):
        out[f.stem] = Image.open(f).convert('RGBA')
    if not out:
        raise SystemExit(f'\n  no traits in {d} — generate them first\n')
    return out


def normalize_outfit(img: Image.Image) -> Image.Image:
    """Scale/position the character to a canonical frame."""
    bbox = img.getchannel('A').getbbox()
    if bbox is None:
        raise ValueError('outfit layer is fully transparent')
    char = img.crop(bbox)
    scale = CHAR_HEIGHT / char.height
    char = char.resize((max(1, round(char.width * scale)), CHAR_HEIGHT), Image.LANCZOS)
    canvas = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.alpha_composite(char, ((CANVAS - char.width) // 2, BASELINE - CHAR_HEIGHT))
    return canvas


def head_box(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of the lavender head blob (searched in the top 60%)."""
    small = img.resize((256, 256))
    px = small.load()
    xs, ys = [], []
    for y in range(150):
        for x in range(256):
            r, g, b, a = px[x, y]
            if a > 200 and abs(r - HEAD_RGB[0]) < HEAD_TOL and abs(g - HEAD_RGB[1]) < HEAD_TOL and abs(b - HEAD_RGB[2]) < HEAD_TOL:
                xs.append(x)
                ys.append(y)
    if len(xs) < 300:
        raise ValueError('no head blob found — outfit layer may be off-model')
    s = CANVAS / 256
    return round(min(xs) * s), round(min(ys) * s), round(max(xs) * s), round(max(ys) * s)


def place_eyes(canvas: Image.Image, eyes: Image.Image, head: tuple[int, int, int, int]) -> None:
    hx0, hy0, hx1, hy1 = head
    hw, hh = hx1 - hx0, hy1 - hy0
    ebox = eyes.getchannel('A').getbbox()
    art = eyes.crop(ebox)
    w = max(1, round(hw * EYES_WIDTH_FRAC))
    h = max(1, round(art.height * w / art.width))
    art = art.resize((w, h), Image.LANCZOS)
    cx = hx0 + hw // 2
    cy = hy0 + round(hh * EYES_CY_FRAC)
    canvas.alpha_composite(art, (cx - w // 2, cy - h // 2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=333)
    ap.add_argument('--seed', default='mofo-trait-map-v1')
    ap.add_argument('--out', default='collection')
    ap.add_argument('--name', default='mofo')
    args = ap.parse_args()

    backgrounds = load_dir(TRAITS / 'background')
    outfits = load_dir(TRAITS / 'outfit')
    eyes = load_dir(TRAITS / 'eyes')

    # ---- THE MAP: every combo, seeded shuffle, take N — unique by design ----
    combos = list(product(sorted(outfits), sorted(eyes), sorted(backgrounds)))
    total = len(combos)
    if args.count > total:
        raise SystemExit(f'\n  asked for {args.count} but only {total} combos exist\n')
    random.Random(args.seed).shuffle(combos)
    chosen = combos[: args.count]

    print(f'\n  combo space  {len(outfits)} outfits x {len(eyes)} eyes x {len(backgrounds)} bgs = {total}')
    print(f'  minting      {len(chosen)} (seed "{args.seed}" — same seed, same set, forever)\n')

    # Normalize each outfit once, detect its head once.
    prepared: dict[str, tuple[Image.Image, tuple[int, int, int, int]]] = {}
    for name, img in outfits.items():
        norm = normalize_outfit(img)
        prepared[name] = (norm, head_box(norm))

    out_dir = ROOT / args.out
    out_dir.mkdir(exist_ok=True)
    counts: dict[str, Counter] = {'Outfit': Counter(), 'Eyes': Counter(), 'Background': Counter()}

    for i, (o, e, b) in enumerate(chosen):
        canvas = Image.new('RGBA', (CANVAS, CANVAS))
        canvas.alpha_composite(backgrounds[b].convert('RGBA'))
        body, head = prepared[o]
        canvas.alpha_composite(body)
        place_eyes(canvas, eyes[e], head)
        canvas.convert('RGB').save(out_dir / f'{i}.png', 'PNG', optimize=True)

        attrs = [
            {'trait_type': 'Outfit', 'value': o.replace('-', ' ')},
            {'trait_type': 'Eyes', 'value': e.replace('-', ' ')},
            {'trait_type': 'Background', 'value': b.replace('-', ' ')},
        ]
        (out_dir / f'{i}.json').write_text(json.dumps({
            'name': f'{args.name} #{i}',
            'description': 'mofo. free mint. figure-eight head, fomo eyes.',
            'image': f'{i}.png',
            'attributes': attrs,
        }, indent=2), encoding='utf-8')
        counts['Outfit'][o] += 1
        counts['Eyes'][e] += 1
        counts['Background'][b] += 1
        if (i + 1) % 50 == 0 or i + 1 == len(chosen):
            print(f'  composed {i + 1}/{len(chosen)}')

    with open(out_dir / '_trait-counts.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['trait_type', 'value', 'count', 'pct'])
        for label, c in counts.items():
            for v, n in c.most_common():
                w.writerow([label, v, n, round(100 * n / len(chosen), 2)])

    print(f'\n  -> {args.out}/  ({len(chosen)} png+json pairs, launchmynft-ready)')
    print(f'  -> {args.out}/_trait-counts.csv  (rarity table — do not upload this file)\n')


if __name__ == '__main__':
    main()
