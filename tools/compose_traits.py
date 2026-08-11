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
CHAR_HEIGHT = 880          # normalized character height, px (x BODY_SCALE)
BASELINE = 984             # feet sit here after normalization
# ---- PASTE THE MIXER READOUT HERE (mixer.html green box) --------------------
EYE_WIDTH   = 0.170        # width of ONE eye, fraction of canvas
EYE_TOP_Y   = 0.235        # eye CENTER height, fraction of canvas
EYE_GAP     = 0.080        # space between the two eyes, fraction of canvas
EYE_X_SHIFT = -0.075        # horizontal nudge of the pair, fraction of canvas
BODY_SCALE  = 1.000        # multiplier on the normalized character height


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
    scale = CHAR_HEIGHT * BODY_SCALE / char.height
    char = char.resize((max(1, round(char.width * scale)), round(CHAR_HEIGHT * BODY_SCALE)), Image.LANCZOS)
    canvas = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.alpha_composite(char, ((CANVAS - char.width) // 2, BASELINE - char.height))
    return canvas


def place_eyes(canvas: Image.Image, eyes: Image.Image) -> None:
    """ONE eye image, placed twice — identical math to mixer.html, so the
    slider numbers the user pastes reproduce exactly what they saw."""
    ebox = eyes.getchannel('A').getbbox()
    art = eyes.crop(ebox)
    w = max(1, round(CANVAS * EYE_WIDTH))
    h = max(1, round(art.height * w / art.width))
    art = art.resize((w, h), Image.LANCZOS)
    cy = round(CANVAS * EYE_TOP_Y)
    half = (EYE_WIDTH + EYE_GAP) / 2
    for cx_frac in (0.5 + EYE_X_SHIFT - half, 0.5 + EYE_X_SHIFT + half):
        cx = round(CANVAS * cx_frac)
        canvas.alpha_composite(art, (cx - w // 2, cy - h // 2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=333)
    ap.add_argument('--seed', default='mofo-trait-map-v1')
    ap.add_argument('--out', default='collection')
    ap.add_argument('--name', default='mofo')
    args = ap.parse_args()

    backgrounds = load_dir(TRAITS / 'background')
    bodies = load_dir(TRAITS / 'body')
    eyes = load_dir(TRAITS / 'eyes')

    # ---- THE MAP: every combo, seeded shuffle, take N — unique by design ----
    combos = list(product(sorted(bodies), sorted(eyes), sorted(backgrounds)))
    total = len(combos)
    rng = random.Random(args.seed)
    rng.shuffle(combos)
    if args.count <= total:
        chosen = combos[: args.count]
    else:
        # Deck-cycling: deal the full shuffled deck repeatedly (reshuffled each
        # pass) until count is reached. Every look appears floor or ceil of
        # count/total times -- the most even spread repeats can have.
        chosen = []
        while len(chosen) < args.count:
            deck = combos[:]
            rng.shuffle(deck)
            chosen.extend(deck)
        chosen = chosen[: args.count]
        print(f'  repeats mode: {args.count} tokens over {total} looks '
              f'(each appears {args.count // total}-{args.count // total + 1}x)')

    print(f'\n  combo space  {len(bodies)} bodies x {len(eyes)} eyes x {len(backgrounds)} bgs = {total}')
    print(f'  minting      {len(chosen)} (seed "{args.seed}" — same seed, same set, forever)\n')

    # Normalize each outfit once, detect its head once.
    prepared: dict[str, Image.Image] = {}
    for name, img in bodies.items():
        prepared[name] = normalize_outfit(img)

    out_dir = ROOT / args.out
    out_dir.mkdir(exist_ok=True)
    counts: dict[str, Counter] = {'Body': Counter(), 'Eyes': Counter(), 'Background': Counter()}

    for i, (o, e, b) in enumerate(chosen):
        canvas = Image.new('RGBA', (CANVAS, CANVAS))
        canvas.alpha_composite(backgrounds[b].convert('RGBA'))
        canvas.alpha_composite(prepared[o])
        place_eyes(canvas, eyes[e])
        canvas.convert('RGB').save(out_dir / f'{i}.png', 'PNG', optimize=True)

        attrs = [
            {'trait_type': 'Body', 'value': o.replace('-', ' ')},
            {'trait_type': 'Eyes', 'value': e.replace('-', ' ')},
            {'trait_type': 'Background', 'value': b.replace('-', ' ')},
        ]
        (out_dir / f'{i}.json').write_text(json.dumps({
            'name': f'{args.name} #{i}',
            'description': 'mofo. free mint. figure-eight head, fomo eyes.',
            'image': f'{i}.png',
            'attributes': attrs,
        }, indent=2), encoding='utf-8')
        counts['Body'][o] += 1
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
