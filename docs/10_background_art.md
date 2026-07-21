# Background Art

Backgrounds appear **behind narration only** — dialogue beats where the player
is reading and clicking Next. Coding challenges and interactive puzzles keep a
clean parchment page so nothing competes with the work.

## How it works

```
story/*.scene       background: ancient_library.png
        │
        ▼
assets/backgrounds/ancient_library.png
        │
        ▼
GET /assets/backgrounds/ancient_library.png     (StaticFiles mount)
        │
        ▼
<SceneBackground> — crossfade + slow drift behind the dialogue
```

`background:` may appear **more than once in a scene**. The first sets the
opening image; each later one is a beat that changes location mid-scene, so a
chapter can move without being split into separate files:

```text
background: ruins.png
dialogue:
"The dragon folds its enormous wings."

background: sky_summons.jpg
dialogue:
"A pillar of light erupts from the ground beneath you."

background: ancient_library.png
dialogue:
"An endless hall materializes around you."
```

A location change also forces a new dialogue block, so the reveal lands on its
own beat rather than mid-paragraph.

Missing files are reported at startup (`[asset warning] ...`) rather than
failing silently to a black screen.

## Characters are shown through the background

There is no cut-out portrait layer. When a character enters, the scene
**becomes** their art:

```text
dialogue:
"The world fades into darkness."
"..."

background: dragon_celestial.jpg

dialogue:
"A pair of enormous golden eyes open before you."
```

This keeps one visual system instead of two, and lets a character
illustration read at full size rather than as a thumbnail.

## Aspect-aware fitting

Scene art is landscape; character art is portrait (the celestial dragon is
768×1344). Cropping the latter to fill a widescreen viewport shows a narrow
band of its chest — the dragon effectively invisible.

So each image is **measured on load** and fitted accordingly:

| Condition | Mode | Result |
|---|---|---|
| Portrait art (aspect < 0.95) on a landscape screen | `contain` over a blurred copy of itself | Whole subject visible, frame still full |
| Everything else | `cover` | Fills edge to edge, no bars |

The blurred backdrop is the same image scaled up and blurred 38px, so tall art
never sits against dead space.

The rule is **categorical, not a distance threshold**, on purpose. Most scene
art here is square (1024×1024), which lands almost exactly on any reasonable
numeric tolerance — a threshold would flip those images between filling and
letterboxing on a mere window resize. Only genuinely portrait art, where
cropping to fill destroys the subject, is contained.

| Asset | Size | Fit |
|---|---|---|
| `dragon_celestial.jpg` | 768×1376 | `contain` |
| `elder_mage.png` | 1123×1589 | `contain` |
| `ruins.png`, `ancient_library.png`, `forest_gate.png` | 1024×1024 | `cover` |
| `deep_forest.jpg`, `sky_summons.jpg`, `sage_reading.jpg` | landscape / square | `cover` |

## Presentation

The source art is dark, saturated anime fantasy; the UI is light parchment.
They are reconciled by treating every image as a **printed plate bound into
the manuscript**, not a screenshot behind a window:

| Treatment | Value | Why |
|---|---|---|
| Warm tint | `sepia(0.18) saturate(0.98) brightness(0.94)` | Pulls the art toward the parchment palette |
| Vignette | radial + linear scrim | Focuses the centre, darkens where text sits |
| Grain | same `--grain` SVG as the UI | Unifies image and page as one printed surface |
| Entrance | 1.4s push-in from `scale(1.08)` | A new location arrives, it does not just appear |
| Drift | 26s Ken Burns (`cover`) / 18s float (`contain`) | Keeps a still image alive under narration |
| Motes | 38s drifting particle field | The air itself moving |
| Transition | 1.2s crossfade, two plates | Locations dissolve instead of flashing |

All of it is disabled under `prefers-reduced-motion`.

## Current mapping

17 background changes across the game — locations shift as the story moves
rather than holding one plate per chapter.

| Scene | Backgrounds, in order |
|---|---|
| `awakening` | `night_forest.avif` → `night_valley.avif` → `ruins.png` |
| `chapter_1_dragon` | `ruins.png` → **`dragon_celestial.jpg`** (the descent) |
| `chapter_1_dragon_trial` | `dragon_celestial.jpg` |
| `chapter_1_trial_failed` | `dragon_celestial.jpg` → `ruins.png` (the light drains) |
| `chapter_1b_wisdom_of_system` | `dragon_celestial.jpg` → `sky_summons.jpg` → `ancient_library.png` → `sage_reading.jpg` → `ancient_library.png` → `sage_reading.jpg` → `ancient_library.png` |
| `chapter_2_trial_of_choice` | `valley_vista.jpg` → `green_valley.jpg` → `deep_forest.jpg` → `forest_gate.png` → `elder_mage.png` → `forest_gate.png` |

Chapter 2 opens as a **journey**: the player leaves the Sage's hall onto a
high vista, walks down through open valley, and only then descends into the
forest where the cry comes from. The narration was rewritten to match — it
previously put the player among trees from the first line, which contradicted
the vista art.

Character art alternates with location art so the Sage and the Elder are
*seen* at the moments they speak, then the camera returns to the room.

## Asset audit

**Formats:** `.png`, `.jpg` and `.avif` all work — the assets mount serves
whatever is on disk and Python 3.13 resolves `.avif` to `image/avif`
correctly. AVIF is the smallest of the three (the two night plates are ~50KB
each versus ~800KB for the square PNGs), so it is a good default for new art.

**In use (clean, no watermark):**

- `night_forest.avif` — dark forest, moonlight through branches, fireflies. Waking.
- `night_valley.avif` — night valley, crescent moon, black mountains. The world revealed.
- `ruins.png` — moonlit floating ruins, portal glow. Awakening.
- `ancient_library.png` — floating shelves, orbiting runes, crystals. Near-perfect match for the Sage's hall as written.
- `forest_gate.png` — runed stone gate on a mountain. Exactly the Gate of Choices.
- `sky_summons.jpg` — figure beneath a descending pillar of light. The dissolve.
- `deep_forest.jpg` — sunlit forest, small cloaked figure. Chapter 2 approach.
- `dragon_celestial.jpg` — celestial dragon, human silhouette beneath. **Portrait aspect** → `contain` fit.
- `sage_reading.jpg` — robed elder with an open book. The Sage.
- `elder_mage.png` — cloaked mage casting. **Portrait aspect** → `contain` fit. The Elder at the Gate.

**In use, but watermarked.** These carry a burned-in `stablediffusionweb.com`
mark in the lower right. Used at the author's explicit direction — **replace
before any public release**:

- `valley_vista.jpg` (from `7afa3047-…jpg`) — Chapter 2 arrival
- `green_valley.jpg` (from `c6c0b531-…jpg`) — Chapter 2 walk

**Not wired in:**

- `a036ec49-…jpg` — watermarked, and `valley_vista.jpg` covers the same beat
- `images.jpg` — carries a Craiyon mark

**Not backgrounds:**

- `ChatGPT Image Jul 21…png` — a 9-panel **System UI kit** (ALARM, SYSTEM, NOTIFICATION, SKILL LEARNED, STATUS, WARNING, ITEM OBTAINED, LEVEL UP, ISEKAI ARRIVAL). This is a styling reference for the `===== SYSTEM UPDATE =====` banners the story uses, not a scene image. See "Next steps".
- `image_system.png` — a crop of the same sheet.
- `393x577.webp` — portrait aspect; would crop badly as a full-bleed background.

## Optional: wide-format versions

The dragon and elder illustrations are portrait-orientation, so they render
in `contain` mode against a blurred backdrop. That works and keeps the whole
subject visible — but a **landscape** version of each would fill the frame
edge to edge and look better still.

These images do not exist yet and were **not generated here** (no image
generation is available in this environment). Prompts below match the
established style — moonlit, painterly anime fantasy, floating islands,
cyan-and-gold key light — and the exact scene copy.

### `dragon_trial.png` — `chapter_1_dragon_trial`
> Painterly anime fantasy background, moonlit night. Thousands of small
> glowing translucent human figures standing in long winding processions
> across floating islands far below, seen from above. A vast dragon
> silhouette with spread wings framing the top of the image, backlit by a
> pale moon. Cyan and gold light, heavy atmospheric depth, cinematic wide
> shot, empty lower third.

### `trial_failed.png` — `chapter_1_trial_failed`
> Painterly anime fantasy background, cold desaturated night. Cracked and
> crumbling floating stone ruins with their magic gone dark, extinguished
> runes, grey mist pouring over broken edges, a single dying ember of light.
> Muted blue-grey palette, almost monochrome, heavy fog, sense of loss and
> aftermath. Wide cinematic composition, empty lower third.

### `sage_hall_close.png` — optional, Lesson beats
> Painterly anime fantasy interior. Close view inside an endless library of
> floating bookshelves, a tall figure in white hooded robes standing with
> back turned at the centre, surrounded by drifting glowing runes and small
> floating wooden chests. Cyan and warm gold light, deep atmospheric
> perspective, cinematic, empty lower third.

**To add one:** drop the file into `assets/backgrounds/`, reference it by
filename from a `.scene`, restart the backend. No code change.

## Next steps available

- **System panel styling.** The provided UI kit maps directly onto the
  `===== SYSTEM UPDATE =====` / `SKILL LEARNED` / `CHAPTER COMPLETE` banners
  already written into the scenes. Rendering those as bordered system panels
  instead of plain narrator lines would be a strong, cheap win.
- **Per-speaker character art.** `assets/characters/` is empty; the Sage, the
  Dragon and the Old Man all have distinct voices already wired into the
  dialogue nameplates.
