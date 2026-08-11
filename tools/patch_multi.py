"""Move trait picking out of Claude into code randomness (fixes 'only chefs').

An LLM handed the identical request every run collapses onto favourite picks —
day one produced chefs repeatedly and seed 417 twice in one batch. After this
patch, Math.random() in the fan-out node rolls seed/outfit/pose/prop/headwear/
feet/background per item (outfits dealt without replacement within a batch),
and Claude only writes prose for the picks it is handed. The sidecar becomes
real JSON metadata, which is what the launchmynft packager ingests.

    python tools/patch_multi.py
"""
import json
from pathlib import Path

F = Path(__file__).resolve().parent.parent / 'workflow' / 'mofo-nft-generator-multi.json'
wf = json.loads(F.read_text(encoding='utf-8'))

FANOUT_JS = """// HOW MANY IMAGES PER EXECUTION. Every node downstream runs once per item.
const COPIES = 5;

// THE DICE LIVE HERE, NOT IN THE LLM. Asked to "pick randomly", a language
// model receiving the identical request every run collapses onto favourites --
// day one produced chefs over and over and seed 417 twice in one batch.
// Math.random() has no favourites. Claude only writes prose for these picks.
const OUTFITS = [
  'a charcoal business suit with a white shirt and dark tie',
  'a bulky white spacesuit with a segmented chest panel and blue trim',
  'a white double-breasted chef jacket with black buttons',
  'a patterned indigo kimono with a wide obi sash',
  'a brown leather biker jacket with silver zips over a white tee',
  'loose teal surgical scrubs with a V neck',
  'navy mechanic overalls over a white undershirt',
  'a charcoal pilot uniform with gold shoulder stripes',
  'a tan cowboy outfit with a fringed suede vest',
  'a black and blue diving wetsuit with panelled seams',
  'polished steel knight armor with segmented plates, carrying no weapons',
  'a black tracksuit with white racing stripes down sleeves and legs',
  'a white lab coat over a pale blue shirt',
  'a blue mail carrier uniform with a shoulder satchel',
  'a crimson boxing robe worn open over black boxing shorts',
  'a deep blue wizard robe with wide sleeves and a rope belt',
  'charcoal firefighter turnout gear with reflective yellow bands',
  'a green and white football kit with numbered shorts',
  'a draped cream toga pinned at one shoulder',
  'a thick olive winter parka with a fur-trimmed hood worn down',
];
const POSES = [
  'waving with one glove', 'arms crossed on the chest', 'hands on hips',
  'pointing forward with one glove', 'giving a thumbs up', 'saluting',
  'shrugging with both gloves turned up', 'walking sideways',
  'both arms raised in celebration', 'standing at attention',
  'scratching the back of the head', 'mid-jump with both gloves up',
];
const PROPS = [
  null, null, null, 'holding a briefcase', 'holding a coffee mug',
  'with a skateboard standing beside', 'holding a closed umbrella',
  'holding a guitar', 'holding a fishing rod', 'holding an open laptop',
  'holding a food tray out in front', 'holding a red fire extinguisher',
  'holding a microphone', 'with a rolling suitcase beside',
  'holding a butterfly net', 'holding a thick closed book',
  'holding a balloon on a string', 'holding a broom', 'holding a racket',
];
const HEADWEAR = [
  null, null, 'a cap', 'black over-ear headphones', 'a yellow hard hat',
  'a bandana tied across the top', 'a gold crown', 'a tall white chef hat',
  'a grey ushanka', 'a black top hat', 'a headband with antennae',
  'a white forehead wrap',
];
const FEET = [
  'black rounded boots', 'white sneakers', 'tall black boots',
  'flat sandals', 'ice skates', 'bare glove-style feet',
];
const BACKGROUNDS = [
  'dark navy #14142E', 'deep red #7A1F2B', 'forest green #1E4D3B',
  'burnt orange #C4552E', 'plum #3B2A5C', 'mustard #D9B94C',
  'teal #2F6E8F', 'magenta #8E4B7A', 'rust #B0562E',
  'near black #1A1A1A', 'warm sand #E3D5C0', 'olive #4A5D23',
];

const pick = (a) => a[Math.floor(Math.random() * a.length)];
// Outfits dealt without replacement: one batch never repeats an outfit.
const deck = [...OUTFITS].sort(() => Math.random() - 0.5);

const src = $input.all()[0];
return Array.from({ length: COPIES }, (_, i) => ({
  json: {
    batchIndex: i + 1,
    seed: 1 + Math.floor(Math.random() * 999),
    outfit: deck[i % deck.length],
    pose: pick(POSES),
    prop: pick(PROPS),
    headwear: pick(HEADWEAR),
    feet: pick(FEET),
    background: pick(BACKGROUNDS),
  },
  binary: src.binary,
}));"""

PREP_JS = """// Build one Claude request per item. The picks were rolled by code in the
// fan-out node; Claude's only job is to look at the two references and write
// clean prose for exactly those picks.
const lockedCore = [
  '- head: two intersecting circles forming a figure-eight / infinity silhouette, very light lavender-white #E8EAFB, large relative to the small mascot-proportioned body',
  '- eyes: two black slanted parallelogram shapes with rounded corners, one inside each lobe, tilted to the right, color #0B0B1E, BOTH LOOKING TO THE LEFT, exactly as in image 2',
  '- the eyes are completely flat solid black: no highlights, no glints, no catchlights, no white shapes inside the eyes',
  '- no mouth, nose, ears, eyebrows, or hair',
  '- hands: white four-fingered cartoon gloves',
  '- flat vector cartoon, retro mascot, thick uniform black outline, no gradients, no shadows, no textures',
  '- full body, centered, square 1:1, no text, logos, captions, or watermarks',
  '- never include weapons, brand names, or real people',
].join('\\n');

const specFor = (p) => [
  'Two references are attached: image 1 defines the style and body build, image 2 defines the head shape and eyes.',
  'Write ONE image-generation prompt in English, a single paragraph of 90-150 words, for this exact character. Start the paragraph with "Seed: ' + p.seed + '."',
  '',
  'LOCKED CORE (spell all of it out explicitly):',
  lockedCore,
  '',
  'MANDATORY PICKS for this image - use every one of them, substitute nothing:',
  '- outfit: ' + p.outfit,
  '- pose: ' + p.pose,
  '- prop: ' + (p.prop || 'none'),
  '- head accessory: ' + (p.headwear ? p.headwear + ' (sits on TOP of the figure-eight head, never covers the eyes)' : 'none'),
  '- footwear: ' + p.feet,
  '- background: one flat solid ' + p.background + ', no patterns, no vignette',
  '',
  'Return only the prompt text. No headings, comments, quotes or explanations.',
].join('\\n');

const character = await this.helpers.getBinaryDataBuffer(0, 'character');
const eyes = await this.helpers.getBinaryDataBuffer(0, 'eyes');
const cb64 = character.toString('base64');
const eb64 = eyes.toString('base64');

return $input.all().map((item) => ({
  json: {
    ...item.json,
    claudeBody: {
      model: 'claude-sonnet-5',
      max_tokens: 1024,
      messages: [
        {
          role: 'user',
          content: [
            { type: 'image', source: { type: 'base64', media_type: 'image/png', data: cb64 } },
            { type: 'image', source: { type: 'base64', media_type: 'image/png', data: eb64 } },
            { type: 'text', text: specFor(item.json) },
          ],
        },
      ],
    },
  },
  binary: item.binary,
}));"""

EXTRACT_JS = """// One prompt per item. The merge upstream combined Claude's response with the
// picks the dice rolled, so this node can emit a REAL metadata sidecar (JSON
// with the traits) instead of a bare prompt dump - which is exactly the shape
// the launchmynft packager ingests.
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
return $input.all().map((item, idx) => {
  const j = item.json;
  const prompt = (j.content || [])
    .filter((c) => c.type === 'text')
    .map((c) => c.text)
    .join(' ')
    .trim();
  if (!prompt) throw new Error('Claude returned no prompt text: ' + JSON.stringify(j).slice(0, 300));
  const base = 'mofo-s' + j.seed + '-' + stamp + '-' + String(idx + 1).padStart(2, '0');
  const sidecar = JSON.stringify({
    seed: j.seed, outfit: j.outfit, pose: j.pose, prop: j.prop,
    headwear: j.headwear, feet: j.feet, background: j.background,
    prompt,
  }, null, 2);
  return {
    json: { prompt, sidecar, seed: j.seed, fileName: base + '.png', promptFile: base + '.json' },
    binary: item.binary,
  };
});"""

count = 0
for n in wf['nodes']:
    if n['name'] == 'Fan out x5':
        n['parameters']['jsCode'] = FANOUT_JS
        count += 1
    elif n['name'] == 'Prep Claude Request':
        n['parameters']['jsCode'] = PREP_JS
        count += 1
    elif n['name'] == 'Extract Prompt':
        n['parameters']['jsCode'] = EXTRACT_JS
        count += 1
    elif n['name'] == 'Commit prompt sidecar':
        n['parameters']['fileContent'] = "={{ $('Extract Prompt').item.json.sidecar }}"
        count += 1

assert count == 4, f'patched {count} nodes, expected 4'
with open(F, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(wf, f, indent=2)

d = json.loads(F.read_text(encoding='utf-8'))
for n in d['nodes']:
    if n['type'].endswith('.code'):
        js = n['parameters']['jsCode']
        assert js.count('{') == js.count('}'), 'braces: ' + n['name']
        assert js.count('(') == js.count(')'), 'parens: ' + n['name']
print('patched 4 nodes, JS balanced, JSON valid')
