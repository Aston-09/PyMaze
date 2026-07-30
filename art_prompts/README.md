# PyBe Art Prompts — High-Res Pixel Art

Prompts for generating scene backgrounds and characters in **Gemini / Nano Banana Pro**,
in a high-resolution pixelated 16-bit-JRPG style matching the reference art.

## How this is organised (deduped, not per-chapter)

Backgrounds and characters are reused across many chapters, so there is **one file per
distinct location/character**, not one per chapter. Each file lists which chapters use it.

- `backgrounds/` — 11 scene locations. Each file has a **base prompt** + **3–5 animation
  frames** (subtle deltas: drifting clouds, pulsing light, rising mist). Generate the base,
  then the frames, and cross-fade/loop them in the frontend for the "dynamic" feel.
- `characters/` — 12 NPCs. Each has a portrait prompt + a short idle-loop (blink / breathe).

## Shared STYLE block (already appended to every prompt file)

> high-resolution pixel art, richly detailed 16-bit SNES-era JRPG style, crisp defined
> pixels with clean edges, vibrant saturated fantasy palette, smooth dithered gradients in
> sky and shadow, strong directional lighting with rim light, layered parallax depth,
> cinematic fantasy atmosphere.

## Shared NEGATIVE prompt (use for all)

> blurry, smooth photographic rendering, 3D render, realistic photo, text, letters,
> watermark, signature, UI, HUD, health bars, jpeg artifacts, extra limbs, deformed hands.

## Aspect ratios
- Backgrounds: **16:9**
- Characters: **1:1** (full-body or portrait, transparent or flat-color background)

## Animation tip
Keep the base composition **identical** across frames of one location — only move the
element named in each frame. Same seed + low denoise on the frame deltas keeps pixels stable.
