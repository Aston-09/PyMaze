# Asset Pipeline

All media assets (images, music, sounds, animations) must be decoupled from the engine source code.

## Folder Structure
```text
assets/
    backgrounds/
    characters/
    music/
    sound/
    animations/
```

## Referencing Assets
Story `.scene` files should reference assets by filename only. 
No absolute paths or relative file traversals should be hardcoded in the story files.

Example from a `.scene` file:
```text
background: ruins.png
music: dragon_theme.mp3
npc_image: dragon.png
```

## Loading Mechanism

The `assets/` directory is mounted directly by the API as static files:

```python
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
```

A scene's `background: ruins.png` therefore resolves in the client to
`GET /assets/backgrounds/ruins.png`. There is no asset-loader module and no
build step — the filesystem *is* the manifest, and the browser handles caching
via normal HTTP.

Adding an asset is dropping a file into the correct folder and typing its name
into a `.scene`.

**Content hot-reload:** `story/`, `challenges/` and `interactions/` are
re-read whenever their files change on disk. `uvicorn --reload` only watches
`*.py`, so without this an edited `.scene` would sit invisible behind a
running server — the text updates on restart, but a background or mission you
just added simply isn't there, with no error to explain why. Save the file,
refresh the page. See `backend/app/engine/content.py`.

**Startup validation:** the engine checks every `background:` referenced by
any scene against what is actually on disk and prints an `[asset warning]` for
each miss, so a typo surfaces as a log line instead of a black screen.

## Backgrounds

Backgrounds render behind **narration and dialogue only**; challenge and
interaction beats keep a clean page. `background:` may appear multiple times
in one scene to change location mid-chapter.

Full specification, current mapping, and the art audit:
[10_background_art.md](10_background_art.md).
