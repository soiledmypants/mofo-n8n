"""Finalize the mofo collection: 20 backgrounds, repeats mode, compose 1111.

    python tools/finalize_1111.py

1. Adds 10 new flat background colors (20 total -> 300 unique looks).
2. Registers them in the mixer dropdown.
3. Adds deck-cycling repeats to the composer: the shuffled deck of all unique
   combos is dealt over and over until `count` is reached, so at 1111 over 300
   looks every combo appears exactly 3 or 4 times — the most even spread
   possible, no look accidentally rare, no look accidentally spammed.
4. Composes the full 1111 with the user's locked mixer numbers.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

# ---- 1. new backgrounds -----------------------------------------------------
NEW = {
    'sky-blue': '#5FA8E0', 'mint': '#7FD8A4', 'lavender': '#9B8CFF',
    'coral': '#FF6B57', 'sunflower': '#FFC53D', 'cocoa': '#6B4A32',
    'seafoam': '#3FBF9F', 'bubblegum': '#F27BB8', 'steel': '#6E7B8F',
    'midnight-purple': '#241B4F',
}
bg_dir = ROOT / 'traits' / 'background'
for name, hexc in NEW.items():
    Image.new('RGB', (1024, 1024), hexc).save(bg_dir / f'{name}.png')
print(f'backgrounds: +{len(NEW)} -> {len(list(bg_dir.glob("*.png")))} total')

# ---- 2. mixer dropdown ------------------------------------------------------
m = ROOT / 'mixer.html'
s = m.read_text(encoding='utf-8')
OLD_BGS = "const BGS = ['dark-navy','deep-red','forest-green','burnt-orange','plum','mustard','teal','magenta','warm-sand','near-black'];"
NEW_BGS = ("const BGS = ['dark-navy','deep-red','forest-green','burnt-orange','plum','mustard',"
           "'teal','magenta','warm-sand','near-black','sky-blue','mint','lavender','coral',"
           "'sunflower','cocoa','seafoam','bubblegum','steel','midnight-purple'];")
if OLD_BGS in s:
    m.write_text(s.replace(OLD_BGS, NEW_BGS, 1), encoding='utf-8', newline='\n')
    print('mixer: 20 backgrounds')
else:
    assert NEW_BGS in s, 'mixer BGS list in unexpected state'
    print('mixer: already at 20')

# ---- 3. composer: deck-cycling repeats -------------------------------------
c = ROOT / 'tools' / 'compose_traits.py'
s = c.read_text(encoding='utf-8')
OLD_PICK = """    combos = list(product(sorted(bodies), sorted(eyes), sorted(backgrounds)))
    total = len(combos)
    if args.count > total:
        raise SystemExit(f'\\n  asked for {args.count} but only {total} combos exist\\n')
    random.Random(args.seed).shuffle(combos)
    chosen = combos[: args.count]"""
NEW_PICK = """    combos = list(product(sorted(bodies), sorted(eyes), sorted(backgrounds)))
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
              f'(each appears {args.count // total}-{args.count // total + 1}x)')"""
if OLD_PICK in s:
    s = s.replace(OLD_PICK, NEW_PICK, 1)
    c.write_text(s, encoding='utf-8', newline='\n')
    print('composer: repeats mode added')
else:
    assert 'Deck-cycling' in s, 'composer pick logic in unexpected state'
    print('composer: repeats mode already present')

import ast
ast.parse(c.read_text(encoding='utf-8'))

# ---- 4. compose the collection ---------------------------------------------
import subprocess
import sys
r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'compose_traits.py'),
                    '--count', '1111', '--out', 'collection'],
                   cwd=ROOT, capture_output=True, text=True)
print(r.stdout[-600:])
if r.returncode != 0:
    print(r.stderr[-600:])
    sys.exit(1)

# ---- 5. preview sheet -------------------------------------------------------
from PIL import Image as I
fs = sorted((ROOT / 'collection').glob('*.png'), key=lambda p: int(p.stem))[:20]
cols, cell = 5, 240
rows = (len(fs) + cols - 1) // cols
sheet = I.new('RGB', (cols * cell, rows * cell), (20, 20, 26))
for i, f in enumerate(fs):
    sheet.paste(I.open(f).resize((cell, cell), I.LANCZOS), ((i % cols) * cell, (i // cols) * cell))
sheet.save(ROOT / 'collection-sheet.png')
print(f'sheet: first {len(fs)} of the collection')
