# mofo-n8n

n8n automation that generates **mofo** NFT candidates on a loop — a 1:1 replica
of the Higgsfield canvas graph:

```
[refs/character.png]──┐
                      ├──► Claude (writes a unique 90–150 word prompt) ──► gpt-image-1
[refs/eyes.png]───────┘        both refs are ALSO attached to the image call ──┘
                                                        │
                                    out/mofo-s<seed>-<time>.png + .txt (auto-committed here)
```

The part that keeps the character on-model is that both reference images are
attached to the **image generation call itself** (`/v1/images/edits`), not just
described in text. Claude's only job is the middle node: look at the two refs,
roll a seed, and write one prompt per the locked spec (figure-eight head
`#E8EAFB`, slanted parallelogram eyes `#0B0B1E` looking **left**, flat solid
black, no glints, no weapons, flat hex background).

Every output lands back in [`out/`](out/) with a `.txt` sidecar holding the
exact prompt — the repo itself is the growing collection.

## Setup (once, ~5 minutes)

1. **Import** — n8n → Workflows → *Import from file* →
   [`workflow/mofo-nft-generator.json`](workflow/mofo-nft-generator.json).
2. **Credentials** — create three, then select them on the matching nodes:
   | Node | Credential type | Value |
   |---|---|---|
   | *Claude writes the prompt* | Header Auth | name `x-api-key`, value = your Anthropic API key |
   | *Image Generation* | Header Auth | name `Authorization`, value = `Bearer <your OpenAI key>` |
   | *Commit NFT to repo* + *Commit prompt sidecar* | GitHub | a token with `repo` scope on this repo |
3. **Run** — hit *Execute workflow* on the **Run Once** trigger. One NFT + its
   prompt appear in `out/` within ~2 minutes.
4. **Constant generation** — activate the workflow; the **Every Hour** schedule
   trigger then mints one candidate per hour. Change the interval on that node
   (e.g. every 15 min). Each image costs roughly **$0.04–0.08** at `medium`
   quality — hourly ≈ $1.50/day, so mind the interval.

## Locked character rules (baked into the Claude node)

- Head: two intersecting circles, figure-eight silhouette, `#E8EAFB`, huge vs body
- Eyes: two slanted parallelograms with rounded corners, `#0B0B1E`, tilted right,
  **both looking left, completely flat black — no glints or highlights**
- No mouth / nose / ears / eyebrows / hair; white four-fingered gloves
- Flat vector, thick uniform black outline, no gradients/shadows/textures
- Flat solid hex background, full body, 1:1, no text or watermarks
- **No weapons, brands, or real people** (weapons trip the API's moderation)

What varies per run: outfit, pose, prop, headwear, footwear, background — picked
by Claude under a fresh seed, stated in the prompt, recorded in the sidecar.

## Notes

- The two refs are fetched from this repo's **raw URLs**, which requires the
  repo to stay public. To go private: add a GitHub Header Auth credential to
  the two `Ref` nodes (`Authorization: Bearer <token>`,
  `Accept: application/vnd.github.raw`) and point them at the API contents URL.
- `gpt-image-1` has **no seed parameter** — the `Seed:` line drives Claude's
  choices, not the renderer, so identical prompts still render differently.
- Swap either file in `refs/` and every future generation follows it. Keep the
  filenames.
- Companion repo [`mofo-pfp-forge`](https://github.com/soiledmypants/mofo-pfp-forge)
  holds the deterministic layered pipeline, the verify/repair batch workflow,
  rarity tooling, and the airdrop scripts.
