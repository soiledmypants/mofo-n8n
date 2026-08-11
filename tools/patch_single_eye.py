"""Switch mixer + composer to single-eye placement with a gap control.

The user's eye crops are becoming ONE eye per file; the pair is drawn twice
with a tunable gap, so spacing is a slider instead of being frozen into the
artwork.

    python tools/patch_single_eye.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- mixer -----------------------------------------------------------------
m = ROOT / 'mixer.html'
s = m.read_text(encoding='utf-8')

s = s.replace('      <img id="eyes" alt="">',
              '      <img id="eyeL" alt="">\n      <img id="eyeR" alt="">')
s = s.replace('  #eyes { left: 50%; top: 50%; transform: translate(-50%, -50%); }',
              '  #eyeL, #eyeR { top: 50%; left: 50%; transform: translate(-50%, -50%); }')

s = s.replace('''    <div class="row">
      <label>eye size <span class="val" id="vW"></span></label>
      <input type="range" id="w" min="10" max="80" step="0.5" value="42">
    </div>
    <div>
      <label>eye height <span class="val" id="vY"></span></label>
      <input type="range" id="y" min="5" max="60" step="0.5" value="22">
    </div>
    <div>
      <label>eye left / right <span class="val" id="vX"></span></label>
      <input type="range" id="x" min="-15" max="15" step="0.25" value="0">
    </div>''',
'''    <div class="row">
      <label>eye size (one eye) <span class="val" id="vW"></span></label>
      <input type="range" id="w" min="5" max="40" step="0.25" value="17">
    </div>
    <div>
      <label>eye height <span class="val" id="vY"></span></label>
      <input type="range" id="y" min="5" max="60" step="0.5" value="22">
    </div>
    <div>
      <label>gap between eyes <span class="val" id="vG"></span></label>
      <input type="range" id="g" min="0" max="40" step="0.25" value="10">
    </div>
    <div>
      <label>pair left / right <span class="val" id="vX"></span></label>
      <input type="range" id="x" min="-15" max="15" step="0.25" value="0">
    </div>''')

OLD_UPDATE = """  function update() {
    $('bg').src = 'traits/background/' + $('selBg').value + '.png';
    $('body').src = 'traits/body/' + $('selBody').value + '.png';
    $('eyes').src = 'traits/eyes/' + $('selEyes').value + '.png';

    const w = +$('w').value, y = +$('y').value, x = +$('x').value, s = +$('s').value;
    $('eyes').style.width = w + '%';
    $('eyes').style.top = y + '%';
    $('eyes').style.left = (50 + x) + '%';
    $('body').style.height = s + '%';
    $('vW').textContent = w + '%'; $('vY').textContent = y + '%';
    $('vX').textContent = (x > 0 ? '+' : '') + x + '%'; $('vS').textContent = s + '%';

    $('readout').textContent =
      'EYE_WIDTH   = ' + (w / 100).toFixed(3) + '\\n' +
      'EYE_TOP_Y   = ' + (y / 100).toFixed(3) + '\\n' +
      'EYE_X_SHIFT = ' + (x / 100).toFixed(3) + '\\n' +
      'BODY_SCALE  = ' + (s / 100).toFixed(3) + '\\n' +
      'combo: ' + $('selBody').value + ' / ' + $('selEyes').value + ' / ' + $('selBg').value;
  }"""

NEW_UPDATE = """  function update() {
    $('bg').src = 'traits/background/' + $('selBg').value + '.png';
    $('body').src = 'traits/body/' + $('selBody').value + '.png';
    const src = 'traits/eyes/' + $('selEyes').value + '.png';
    $('eyeL').src = src; $('eyeR').src = src;

    const w = +$('w').value, y = +$('y').value, g = +$('g').value, x = +$('x').value, s = +$('s').value;
    // one image, two placements: pair centered on (50 + x), split by the gap
    const half = (w + g) / 2;
    const pairs = [[$('eyeL'), 50 + x - half], [$('eyeR'), 50 + x + half]];
    for (const [el, cx] of pairs) {
      el.style.width = w + '%';
      el.style.top = y + '%';
      el.style.left = cx + '%';
    }
    $('body').style.height = s + '%';
    $('vW').textContent = w + '%'; $('vY').textContent = y + '%';
    $('vG').textContent = g + '%';
    $('vX').textContent = (x > 0 ? '+' : '') + x + '%'; $('vS').textContent = s + '%';

    $('readout').textContent =
      'EYE_WIDTH   = ' + (w / 100).toFixed(3) + '\\n' +
      'EYE_TOP_Y   = ' + (y / 100).toFixed(3) + '\\n' +
      'EYE_GAP     = ' + (g / 100).toFixed(3) + '\\n' +
      'EYE_X_SHIFT = ' + (x / 100).toFixed(3) + '\\n' +
      'BODY_SCALE  = ' + (s / 100).toFixed(3) + '\\n' +
      'combo: ' + $('selBody').value + ' / ' + $('selEyes').value + ' / ' + $('selBg').value;
  }"""

assert OLD_UPDATE in s, 'update() anchor not found'
s = s.replace(OLD_UPDATE, NEW_UPDATE, 1)

s = s.replace(
    "for (const id of ['selBody','selEyes','selBg','w','y','x','s']) $(id).addEventListener('input', update);",
    "for (const id of ['selBody','selEyes','selBg','w','y','g','x','s']) $(id).addEventListener('input', update);")
s = s.replace(
    "for (const id of ['bg','body','eyes']) $(id).addEventListener('error', markMissing);",
    "for (const id of ['bg','body','eyeL','eyeR']) $(id).addEventListener('error', markMissing);")

m.write_text(s, encoding='utf-8', newline='\n')
assert "$('eyeL')" in s and 'EYE_GAP' in s
print('mixer patched')

# ---- composer ---------------------------------------------------------------
c = ROOT / 'tools' / 'compose_traits.py'
s = c.read_text(encoding='utf-8')

s = s.replace('''EYE_WIDTH   = 0.420        # eye art width, fraction of canvas
EYE_TOP_Y   = 0.220        # eye CENTER height, fraction of canvas
EYE_X_SHIFT = 0.000        # horizontal nudge, fraction of canvas (+right)
BODY_SCALE  = 1.000        # multiplier on the normalized character height''',
'''EYE_WIDTH   = 0.170        # width of ONE eye, fraction of canvas
EYE_TOP_Y   = 0.220        # eye CENTER height, fraction of canvas
EYE_GAP     = 0.100        # space between the two eyes, fraction of canvas
EYE_X_SHIFT = 0.000        # horizontal nudge of the pair, fraction of canvas
BODY_SCALE  = 1.000        # multiplier on the normalized character height''')

OLD_PLACE = '''def place_eyes(canvas: Image.Image, eyes: Image.Image) -> None:
    """Canvas-frame placement — identical math to mixer.html, so the slider
    numbers the user pastes reproduce exactly what they saw."""
    ebox = eyes.getchannel('A').getbbox()
    art = eyes.crop(ebox)
    w = max(1, round(CANVAS * EYE_WIDTH))
    h = max(1, round(art.height * w / art.width))
    art = art.resize((w, h), Image.LANCZOS)
    cx = round(CANVAS * (0.5 + EYE_X_SHIFT))
    cy = round(CANVAS * EYE_TOP_Y)
    canvas.alpha_composite(art, (cx - w // 2, cy - h // 2))'''

NEW_PLACE = '''def place_eyes(canvas: Image.Image, eyes: Image.Image) -> None:
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
        canvas.alpha_composite(art, (cx - w // 2, cy - h // 2))'''

assert OLD_PLACE in s, 'place_eyes anchor not found'
s = s.replace(OLD_PLACE, NEW_PLACE, 1)
c.write_text(s, encoding='utf-8', newline='\n')

import ast
ast.parse(s)
print('composer patched, parses clean')
