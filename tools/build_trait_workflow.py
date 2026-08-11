"""Build workflow/mofo-trait-generator.json — STEP 1: the 10 bodies.

Staged plan (user's call): get 10 complete BODIES right first — full character,
outfit + footwear + white gloves, blank solid head, NO eyes — approve them,
THEN generate the eye styles as step 2 (the EYES dict below stays ready for
that). Backgrounds are flat colors, already committed. No Claude node: trait
prompts are fixed strings, so an LLM adds nothing but cost here.

    python tools/build_trait_workflow.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'workflow' / 'mofo-trait-generator.json'

LOCK = (
    "Flat vector cartoon style, retro mascot look, thick uniform black outline, "
    "no gradients, no shadows, no textures. Fully transparent background - "
    "nothing behind the subject at all. No text, logos, or watermarks."
)

# Each body is a COMPLETE look: outfit + trousers + footwear spelled out.
BODIES = {
    'street':    'a grey pullover hoodie with a kangaroo pocket, black jogger trousers, and chunky white sneakers',
    'tuxedo':    'a black tuxedo jacket with a bow tie and white shirt, black trousers, and shiny black dress shoes',
    'varsity':   'a cream varsity jacket with black raglan sleeves, dark blue jeans, and white sneakers with black laces',
    'puffer':    'a bright blue quilted puffer jacket, black trousers, and chunky black boots',
    'tracksuit': 'a black tracksuit with white racing stripes down the sleeves and legs, and white running shoes',
    'chef':      'a white double-breasted chef jacket with black buttons, grey striped trousers, and black kitchen clogs',
    'hazmat':    'a bright yellow sealed hazmat suit with a dark grey chest control panel, and heavy black rubber boots',
    'cowboy':    'a tan fringed suede vest over a cream shirt, blue jeans with a big belt buckle, and brown cowboy boots',
    'wizard':    'a deep blue wizard robe with wide sleeves and a rope belt, and simple brown sandals peeking out',
    'spacesuit': 'a bulky white spacesuit with a segmented chest panel and blue trim, and big white space boots',
}

EYES = {
    'classic':       'filled completely with flat solid black #0B0B1E',
    'half-lidded':   'flat solid black with the top third cut flat as sleepy half-closed lids',
    'angry':         'flat solid black, angled sharply downward toward the center like a frown',
    'glowing-green': 'filled with flat bright green #3BF07A, no glow effects, just the flat colour',
    'gold':          'filled with flat metallic gold #F2C14E',
    'laser-red':     'filled with flat bright red #E52222',
    'hearts':        'each containing one white heart shape centered on the flat black fill',
    'x-x':           'each replaced by a thick black X mark of the same overall size',
    'star':          'each containing one white four-pointed star centered on the flat black fill',
    'ice-blue':      'filled with flat pale ice blue #A8D8F0',
}

def body_prompt(desc: str) -> str:
    # Gloves stated FIRST and repeated LAST: stating them once mid-prompt still
    # produced outfit-coloured gloves. The head block stays positive-phrased —
    # "no eyes" produced hollow sockets, describing the solid surface did not.
    return (
        "The exact same mascot character as image 1, with large puffy FOUR-FINGERED "
        "CARTOON GLOVES in pure bright WHITE #FFFFFF with black outlines on both hands. "
        "Head formed by two intersecting circles creating a figure-eight silhouette, "
        "large relative to the small body, standing straight with arms at the sides. "
        f"The character wears {desc}. THE HEAD: one solid seamless shape filled with "
        "flat lavender-white #E8EAFB everywhere, a single black outline around its outer "
        "edge ONLY, and a completely plain empty surface like a blank unpainted helmet - "
        "the interior is pure uninterrupted #E8EAFB with zero holes, zero sockets, zero "
        "cutouts, zero shapes, zero lines inside it. REMEMBER THE GLOVES: both hands are "
        "pure snow-white #FFFFFF cartoon gloves, never dark, never black, never the "
        "colour of the clothing, in every single image. Full body, centered. " + LOCK
    )

def eyes_prompt(desc: str) -> str:
    return (
        "ONLY the two eye shapes from image 2, nothing else - no head, no face, no "
        "character, no circle behind them. Two large slanted parallelogram shapes with "
        "rounded corners, tilted to the right, side by side with a small gap, "
        f"{desc}. They fill most of the canvas width. " + LOCK
    )

# STEP 1 renders bodies only. When the user approves them, add the eyes back:
#   + [{'type': 'eyes', 'name': k, 'prompt': eyes_prompt(v)} for k, v in EYES.items()]
items = [{'type': 'body', 'name': k, 'prompt': body_prompt(v)} for k, v in BODIES.items()]

FANOUT_JS = (
    "// 20 fixed trait renders: 10 outfits (blank head) + 10 eye styles.\n"
    "// Prompts are baked in - no LLM needed for fixed strings.\n"
    "const ITEMS = " + json.dumps(items, indent=2) + ";\n"
    "const src = $input.all()[0];\n"
    "return ITEMS.map((t) => ({\n"
    "  json: { ...t, fileName: t.type + '-' + t.name + '.png', filePath: 'traits/' + t.type + '/' + t.name + '.png' },\n"
    "  binary: src.binary,\n"
    "}));"
)

FILTER_JS = """const good = [];
const bad = [];
for (const item of $input.all()) {
  const d = item.json;
  if (d && d.data && d.data[0] && d.data[0].b64_json) good.push(item);
  else bad.push((d && (d.error && d.error.message || d.message)) || 'unknown');
}
if (good.length === 0) throw new Error('every trait render failed - first error: ' + (bad[0] || 'unknown'));
return good;"""

wf = {
    "name": "mofo TRAIT generator (run once)",
    "nodes": [
        {"parameters": {}, "id": "t-run", "name": "Run Once",
         "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [-660, 140]},
        {"parameters": {"url": "https://raw.githubusercontent.com/soiledmypants/mofo-n8n/main/refs/character.png",
                        "options": {"response": {"response": {"responseFormat": "file", "outputPropertyName": "character"}}}},
         "id": "t-ref1", "name": "Ref 1: NFT base", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [-440, 40]},
        {"parameters": {"url": "https://raw.githubusercontent.com/soiledmypants/mofo-n8n/main/refs/eyes.png",
                        "options": {"response": {"response": {"responseFormat": "file", "outputPropertyName": "eyes"}}}},
         "id": "t-ref2", "name": "Ref 2: fomo eyes", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [-440, 240]},
        {"parameters": {"mode": "combine", "combineBy": "combineByPosition", "options": {}},
         "id": "t-merge", "name": "Both refs together", "type": "n8n-nodes-base.merge", "typeVersion": 3, "position": [-220, 140]},
        {"parameters": {"mode": "runOnceForAllItems", "jsCode": FANOUT_JS},
         "id": "t-fan", "name": "Fan out traits", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [0, 140]},
        {"parameters": {
            "method": "POST", "url": "https://api.openai.com/v1/images/edits",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "contentType": "multipart-form-data",
            "bodyParameters": {"parameters": [
                {"name": "model", "value": "gpt-image-1"},
                {"name": "prompt", "value": "={{ $json.prompt }}"},
                {"name": "quality", "value": "medium"},
                {"name": "size", "value": "1024x1024"},
                {"name": "background", "value": "transparent"},
                {"parameterType": "formBinaryData", "name": "image[]", "inputDataFieldName": "character"},
                {"parameterType": "formBinaryData", "name": "image[]", "inputDataFieldName": "eyes"},
            ]},
            "options": {"timeout": 300000, "batching": {"batch": {"batchSize": 1, "batchInterval": 12000}}}},
         "id": "t-img", "name": "Render trait (transparent)", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
         "position": [220, 140], "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000, "onError": "continueRegularOutput"},
        {"parameters": {"mode": "runOnceForAllItems", "jsCode": FILTER_JS},
         "id": "t-keep", "name": "Keep only rendered", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [440, 140]},
        {"parameters": {"operation": "toBinary", "sourceProperty": "data[0].b64_json",
                        "options": {"fileName": "={{ $('Fan out traits').item.json.fileName }}", "mimeType": "image/png"}},
         "id": "t-dec", "name": "Decode PNG", "type": "n8n-nodes-base.convertToFile", "typeVersion": 1.1, "position": [660, 140]},
        {"parameters": {"resource": "file", "operation": "create", "owner": "soiledmypants", "repository": "mofo-n8n",
                        "filePath": "={{ $('Fan out traits').item.json.filePath }}", "binaryData": True,
                        "commitMessage": "={{ 'trait: ' + $('Fan out traits').item.json.fileName }}"},
         "id": "t-gh", "name": "Commit trait", "type": "n8n-nodes-base.github", "typeVersion": 1,
         "position": [880, 140], "onError": "continueRegularOutput"},
    ],
    "connections": {
        "Run Once": {"main": [[{"node": "Ref 1: NFT base", "type": "main", "index": 0},
                               {"node": "Ref 2: fomo eyes", "type": "main", "index": 0}]]},
        "Ref 1: NFT base": {"main": [[{"node": "Both refs together", "type": "main", "index": 0}]]},
        "Ref 2: fomo eyes": {"main": [[{"node": "Both refs together", "type": "main", "index": 1}]]},
        "Both refs together": {"main": [[{"node": "Fan out traits", "type": "main", "index": 0}]]},
        "Fan out traits": {"main": [[{"node": "Render trait (transparent)", "type": "main", "index": 0}]]},
        "Render trait (transparent)": {"main": [[{"node": "Keep only rendered", "type": "main", "index": 0}]]},
        "Keep only rendered": {"main": [[{"node": "Decode PNG", "type": "main", "index": 0}]]},
        "Decode PNG": {"main": [[{"node": "Commit trait", "type": "main", "index": 0}]]},
    },
    "pinData": {},
    "settings": {"executionOrder": "v1"},
}

with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(wf, f, indent=2)

d = json.loads(OUT.read_text(encoding='utf-8'))
names = [n['name'] for n in d['nodes']]
for s, c in d['connections'].items():
    assert s in names, s
    for outs in c['main']:
        for x in outs:
            assert x['node'] in names, f"{s}->{x['node']}"
print(f'wrote {OUT.name}: {len(names)} nodes, {len(items)} trait renders (~$1 one-time)')
