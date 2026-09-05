"""
Sprite Sheet Slicer

Authoring tool, not part of the running engine: splits a combined 2x2
"contact sheet" image — the shape the art generator hands back when asked
for a 4-frame idle loop — into separate frame_N files under the same folder,
so the frontend's existing frame-cycling code (built for background
locations) animates character portraits too, with no code change per
character.

The generator has no real alpha to give: it draws "transparent" as a literal
grey checkerboard, baked into the pixels. There are two ways to take that
back out, and which one applies depends only on the file format the art
arrived in.

**PNG (preferred) — `cut_from_checkerboard`.** The checkerboard survives
intact, and that makes it an asset rather than a nuisance: two known backdrop
tones turn the compositing equation into something solvable, so alpha is
*measured* rather than guessed, and a glow or a feathered wing comes out
exactly as drawn. Drop sheets in art_prompts/incoming/ and run:

    python -m app.engine.sprite_slicer --cut-incoming

**JPEG (legacy) — `matte_all` + `dematte_all`.** Compression smears the
checkerboard into a gradient, so its two tones can no longer be told apart
and the equation above has nothing to bite on. All that is left is to guess a
threshold: paint a vignette over whatever looks like background, then subtract
that vignette again. It works on flat art and fails on anything with a glow,
which is why `crystal` and `system` still carry visible speckle. Art that
matters should be re-exported as PNG and run through the path above.

Run after dropping new JPEG art into assets/characters/<name>/:
    python -m app.engine.sprite_slicer

Verify the maths against synthetic ground truth:
    python -m app.engine.sprite_slicer --selfcheck

Safe to re-run: slicing skips a folder that already holds frame_*.jpg/png
files, and matting skips a folder that already has a `.matted` marker.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[3]
CHARACTERS_DIR = REPO_ROOT / "assets" / "characters"
BACKGROUNDS_DIR = REPO_ROOT / "assets" / "backgrounds"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _line_std(line: Image.Image) -> float:
    """Spread of one 1-pixel row or column — how much it varies along itself."""
    from PIL import ImageStat
    return ImageStat.Stat(line).stddev[0]


# A divider drawn between panels is a solid line, so it barely varies along its
# own length. Measured across every background in the project, real dividers
# score under 2.2 and the flattest line in a genuine single scene scores 10.7,
# so this sits in the gap with room on both sides. Colour is deliberately not
# part of the test: the generator draws the divider black on some sheets and
# white on others.
_DIVIDER_STD_MAX = 6.0
# How far from the exact centre the seam is allowed to sit.
_DIVIDER_SEARCH = 12
# Past this it is not a divider but a band of flat sky or water.
_DIVIDER_MAX_THICKNESS = 24

# Warm-shadow center fading to near-black at the edge. It doesn't need to
# match any one character's palette — every plate shown in-game already
# gets sepia-toned and vignetted again by the frontend's own CSS.
VIGNETTE_INNER = (60, 50, 38)
VIGNETTE_OUTER = (12, 10, 8)

# max(r,g,b) - min(r,g,b) below this reads as "grey". Some characters (the
# dragon's rim-lit wings, the crystal's glowing halo) tint their checkerboard
# with a faint colour cast from an adjacent glow effect, so this sits a bit
# above a literal neutral grey to still catch it.
_SAT_THRESHOLD = 28
# A connected grey patch smaller than this fraction of the frame reads as a
# real costume detail (a buckle, a trim); at or above it, it's background --
# even fully enclosed by a coiled tail or a spread wing.
_MIN_BACKGROUND_FRACTION = 0.001


def _is_sliced(folder: Path) -> bool:
    return any(folder.glob("frame_*.jpg")) or any(folder.glob("frame_*.png"))


def _uniform_run(is_uniform, centre: int, limit: int) -> tuple | None:
    """The stretch of consecutive near-uniform lines straddling `centre`.

    Returns (start, stop) as a half-open range, or None when no uniform line
    sits within the search window or the stretch grows past `limit` — a run
    that wide is a band of flat sky, not a drawn divider.
    """
    seed = None
    for offset in range(_DIVIDER_SEARCH + 1):
        for probe in {centre - offset, centre + offset}:
            if is_uniform(probe):
                seed = probe
                break
        if seed is not None:
            break
    if seed is None:
        return None

    lo = hi = seed
    while is_uniform(lo - 1):
        lo -= 1
        if hi - lo > limit:
            return None
    while is_uniform(hi + 1):
        hi += 1
        if hi - lo > limit:
            return None
    return lo, hi + 1


def _find_divider(im: Image.Image) -> tuple | None:
    """Locate the cross-shaped divider of a 2x2 contact sheet.

    Returns ((y0, y1), (x0, x1)) — the rows and columns the divider occupies,
    to be excluded from every quadrant — or None when the image is a single
    scene. Both axes must show a seam: a lone horizontal line is a horizon,
    not a divider, which is what keeps genuine landscapes out of this. Only
    lines near the centre are measured, so this stays cheap on a big sheet.
    """
    grey = im.convert("L")
    w, h = grey.size

    def row_uniform(y):
        return 0 <= y < h and _line_std(grey.crop((0, y, w, y + 1))) < _DIVIDER_STD_MAX

    def col_uniform(x):
        return 0 <= x < w and _line_std(grey.crop((x, 0, x + 1, h))) < _DIVIDER_STD_MAX

    span_y = _uniform_run(row_uniform, h // 2, _DIVIDER_MAX_THICKNESS)
    span_x = _uniform_run(col_uniform, w // 2, _DIVIDER_MAX_THICKNESS)
    if not span_y or not span_x:
        return None
    return span_y, span_x


# A quadrant may carry a few more flat lines than the seam scan claimed: the
# generator also rules a border around the outside of the whole sheet, and the
# ruled lines are anti-aliased, so their outermost pixels blend into the art
# and score just above the divider threshold. Both show up the same way — flat
# lines hugging an edge — so both come off the same way. Capped so this can
# never bite into a scene that simply opens on flat sky.
_TRIM_MAX = 14


def _flat_border(im: Image.Image) -> tuple:
    """How many flat ruled lines hug each edge, as (left, top, right, bottom)."""
    w, h = im.size
    grey = im.convert("L")

    def count(vertical: bool, from_start: bool) -> int:
        n = 0
        while n < _TRIM_MAX:
            i = n if from_start else (w - 1 - n if vertical else h - 1 - n)
            line = grey.crop((i, 0, i + 1, h)) if vertical else grey.crop((0, i, w, i + 1))
            if _line_std(line) >= _DIVIDER_STD_MAX:
                break
            n += 1
        return n

    return count(True, True), count(False, True), count(True, False), count(False, False)


def _quadrant_boxes(im: Image.Image) -> list:
    """The four crop boxes of a 2x2 sheet, with any divider excluded.

    Falls back to exact halves when no divider is drawn, which is how the
    character sheets were laid out.
    """
    w, h = im.size
    divider = _find_divider(im)
    if divider:
        (y0, y1), (x0, x1) = divider
    else:
        y0 = y1 = h // 2
        x0 = x1 = w // 2
    return [
        (0, 0, x0, y0), (x1, 0, w, y0),
        (0, y1, x0, h), (x1, y1, w, h),
    ]


def _slice_sheet(sheet: Path, out_dir: Path, start_index: int = 1,
                 upscale: int = 1) -> int:
    """Split one 2x2 contact sheet into 4 frame_N files.

    Reading order matches how the generator lays out a 4-panel sheet:
    left-to-right, top-to-bottom (frame_1 = top-left ... frame_4 = bottom-
    right). Returns the next free frame index, so a second sheet for the
    same character (the dragon ships two) continues the sequence instead of
    overwriting it.

    `upscale` enlarges each frame by a whole-number factor with nearest
    neighbour. Every panel here is pixel art, so an integer nearest scale
    invents no detail and softens no edge — it just restores the resolution
    the quadrant lost by being one quarter of a sheet.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(sheet) as im:
        im = im.convert("RGB")
        ruled = _find_divider(im) is not None
        frames = [im.crop(box) for box in _quadrant_boxes(im)]

        if ruled:
            # One trim for all four, taken from the worst edge of any of them.
            # Trimming each to its own measurement would leave the frames
            # different sizes, and the location would then jitter every time
            # the frontend cross-fades from one frame to the next.
            borders = [_flat_border(f) for f in frames]
            left, top, right, bottom = (max(b[i] for b in borders) for i in range(4))
            frames = [
                f.crop((left, top, f.width - right, f.height - bottom)) for f in frames
            ]
            # Belt and braces: a divider that sat off-centre can leave the
            # quadrants a pixel apart, and cycling frames must not resize.
            side = min(f.width for f in frames), min(f.height for f in frames)
            frames = [
                f.crop(((f.width - side[0]) // 2, (f.height - side[1]) // 2,
                        (f.width - side[0]) // 2 + side[0],
                        (f.height - side[1]) // 2 + side[1]))
                for f in frames
            ]

        for i, frame in enumerate(frames):
            if upscale > 1:
                frame = frame.resize(
                    (frame.width * upscale, frame.height * upscale), Image.NEAREST
                )
            frame.save(out_dir / f"frame_{start_index + i}.jpg", quality=92)
    return start_index + 4


def slice_backgrounds(backgrounds_dir: Path = BACKGROUNDS_DIR) -> list:
    """Split any background that is really a 2x2 sheet of animation frames.

    The generator returns a 4-frame idle loop as one composite image, and for
    backgrounds that composite was shipped as-is — so the game rendered the
    whole grid, dividers and all, as a single "location". Each quadrant is
    the same place at a different moment (stars twinkling, a firefly moving),
    which is exactly what the frontend's frame cycling expects to be handed.
    """
    if not backgrounds_dir.is_dir():
        return []

    log = []
    for folder in sorted(p for p in backgrounds_dir.iterdir() if p.is_dir()):
        frames = sorted(folder.glob("frame_*.jpg"), key=_frame_index)
        sheets, keepers = [], []
        for frame in frames:
            with Image.open(frame) as im:
                (sheets if _find_divider(im) else keepers).append(frame)
        if not sheets:
            continue

        # Everything lands in a staging folder first, then comes back as a
        # contiguous frame_1..N. Renaming in place would collide whenever a
        # folder mixes real frames with a sheet that expands into four.
        staged = folder / "_slicing"
        staged.mkdir(exist_ok=True)
        order = 0
        for keeper in keepers:
            order += 1
            keeper.replace(staged / f"keep_{order:03d}.jpg")
        for sheet in sheets:
            _slice_sheet(sheet, staged, order + 1, upscale=2)
            order += 4
            sheet.unlink()

        produced = sorted(staged.iterdir(), key=_frame_index)
        # Every frame in a folder is the same location at a different moment,
        # and they cross-fade into each other. Two sheets trimmed to their own
        # borders would hand back two different sizes, so the location would
        # visibly resize partway through its loop.
        _unify_sizes(produced)
        for i, path in enumerate(produced, start=1):
            path.replace(folder / f"frame_{i}.jpg")
        staged.rmdir()
        log.append(
            f"{folder.name}: split {len(sheets)} sheet(s) -> frame_1..{len(produced)}"
        )

    return log


def _unify_sizes(paths: list) -> None:
    """Centre-crop a set of frames to their common size, in place."""
    sizes = set()
    for path in paths:
        with Image.open(path) as im:
            sizes.add(im.size)
    if len(sizes) <= 1:
        return
    tw = min(w for w, _ in sizes)
    th = min(h for _, h in sizes)
    for path in paths:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if im.size == (tw, th):
                continue
            x = (im.width - tw) // 2
            y = (im.height - th) // 2
            im.crop((x, y, x + tw, y + th)).save(path, quality=92)


def _frame_index(path: Path) -> int:
    """Sort frame_2 before frame_10, and keepers before freshly cut frames."""
    digits = "".join(c for c in path.stem if c.isdigit())
    return int(digits) if digits else 0


def slice_all(characters_dir: Path = CHARACTERS_DIR) -> list:
    """Slice every un-sliced combined sheet under characters_dir.

    Returns one log line per folder touched. The `player` folder is a
    special case one level deeper — male_player.jpg / female_player.jpg each
    become their own frame_1..4 set in a male/ or female/ subfolder, since
    the game shows one or the other depending on what the learner picked.
    """
    if not characters_dir.is_dir():
        return []

    log = []
    for folder in sorted(p for p in characters_dir.iterdir() if p.is_dir()):
        if folder.name == "player":
            for gender in ("male", "female"):
                sheet = folder / f"{gender}_player.jpg"
                out_dir = folder / gender
                if sheet.is_file() and not _is_sliced(out_dir):
                    _slice_sheet(sheet, out_dir)
                    sheet.unlink()
                    log.append(f"player/{gender}: sliced -> frame_1..4, removed source")
            continue

        if _is_sliced(folder):
            continue

        sheets = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
        if not sheets:
            continue

        next_i = 1
        for sheet in sheets:
            next_i = _slice_sheet(sheet, folder, next_i)
        for sheet in sheets:
            sheet.unlink()
        log.append(f"{folder.name}: sliced {len(sheets)} sheet(s) -> frame_1..{next_i - 1}")

    return log


def _make_vignette(size) -> Image.Image:
    """A soft radial glow, built once and reused for every portrait: warm
    near the center where a standing character's mass usually sits, fading
    to near-black at the frame edge."""
    w, h = size
    cx, cy = w / 2, h * 0.55
    max_r = ((w ** 2 + h ** 2) ** 0.5) / 2
    grad = Image.new("RGB", size)
    px = grad.load()
    for y in range(h):
        for x in range(w):
            t = min(1.0, (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / max_r)
            px[x, y] = tuple(
                int(VIGNETTE_INNER[i] + (VIGNETTE_OUTER[i] - VIGNETTE_INNER[i]) * t)
                for i in range(3)
            )
    return grad


def _replace_checkerboard(im: Image.Image, vignette: Image.Image) -> Image.Image:
    """Swap the generator's flat grey checkerboard for `vignette`, leaving
    the character untouched.

    A low-saturation mask marks every checkerboard-like pixel (the checker
    has no hue, at any brightness, so this catches both of its alternating
    tones at once). That mask is then split into its connected patches, each
    classified independently by size: touching the frame's border always
    means background (nothing legitimately reaches the very edge), and
    anything else counts as background only once it's too big to plausibly
    be a costume detail — big enough that a coiled tail or a spread wing
    could fully enclose it without it actually belonging to the character.
    """
    im = im.convert("RGB")
    saturation = im.convert("HSV").split()[1]
    candidates = saturation.point(lambda v: 255 if v <= _SAT_THRESHOLD else 0)

    confirmed = _confirm_background(candidates)
    confirmed = confirmed.filter(ImageFilter.GaussianBlur(1.5))  # soften the cut edge

    return Image.composite(vignette, im, confirmed)


def _confirm_background(candidates: Image.Image) -> Image.Image:
    """Keep only the candidate patches that are really background.

    `candidates` is a white-on-black mask of every pixel that *looks* like
    background. Splitting it into connected patches and judging each one by
    itself is what separates a grey belt buckle from the grey field behind
    the character: touching the frame's border always means background
    (nothing legitimately reaches the very edge), and anything else counts
    only once it is too big to plausibly be a costume detail — big enough
    that a coiled tail or a spread wing could fully enclose it without it
    belonging to the character.
    """
    w, h = candidates.size
    min_area = max(80, int(w * h * _MIN_BACKGROUND_FRACTION))
    working = candidates.copy()

    CANDIDATE, CHARACTER, BACKGROUND, CLAIMED = 255, 0, 254, 128
    while True:
        idx = working.tobytes().find(bytes([CANDIDATE]))
        if idx == -1:
            break
        seed = (idx % w, idx // w)
        touches_border = seed[0] in (0, w - 1) or seed[1] in (0, h - 1)

        ImageDraw.floodfill(working, seed, CLAIMED, thresh=0)
        size = working.histogram()[CLAIMED]

        final = BACKGROUND if (touches_border or size >= min_area) else CHARACTER
        ImageDraw.floodfill(working, seed, final, thresh=0)

    return working.point(lambda v: 255 if v == BACKGROUND else 0)


def matte_all(characters_dir: Path = CHARACTERS_DIR) -> list:
    """Replace the checkerboard in every already-sliced frame, folder by
    folder. Idempotent via a `.matted` marker so re-running after slicing
    fresh art doesn't re-process (and re-compress) frames already done."""
    if not characters_dir.is_dir():
        return []

    vignette = None
    log = []
    for folder in sorted(characters_dir.rglob("*")):
        if not folder.is_dir():
            continue
        frames = sorted(folder.glob("frame_*.jpg"))
        if not frames or (folder / ".matted").exists():
            continue

        if vignette is None:
            with Image.open(frames[0]) as probe:
                vignette = _make_vignette(probe.size)

        for frame in frames:
            with Image.open(frame) as im:
                out = _replace_checkerboard(im, vignette)
            out.save(frame, quality=92)
        (folder / ".matted").touch()
        log.append(f"{folder.relative_to(characters_dir)}: matted {len(frames)} frame(s)")

    return log


# How far a pixel may sit from the regenerated vignette and still count as
# background. The plates are JPEG, so even untouched backdrop drifts a little;
# measured on the shipped art, true backdrop lands within 2 and the character
# is far outside, so this has room either side without eating dark costume.
_DEMATTE_TOLERANCE = 12
# Two kinds of crumb survive into the shipped plates: a dotted crust along the
# frame edge, left by the old matte blurring its mask, and — where the old
# saturation test misfired on a tinted checkerboard — whole squares of
# checkerboard that were never painted over at all. Both are small, and both
# are far smaller than anything drawn on purpose. Measured across the art, the
# smallest deliberate detached object (a potion beside the alchemist) is 1257
# pixels and the largest crumb is 508, so this sits inside that gap.
_MIN_FOREGROUND_FRACTION = 0.0025


def _drop_specks(foreground: Image.Image) -> Image.Image:
    """Clear foreground patches too small to be anything the artist drew.

    The character is one large patch; a deliberately detached prop — a floating
    potion, a hovering rune — is still substantial. Everything below the cut is
    leftover backdrop, wherever in the frame it landed.
    """
    w, h = foreground.size
    min_area = max(80, int(w * h * _MIN_FOREGROUND_FRACTION))
    work = foreground.copy()
    keep = Image.new("L", (w, h), 0)

    while True:
        idx = work.tobytes().find(bytes([255]))
        if idx == -1:
            break
        seed = (idx % w, idx // w)
        ImageDraw.floodfill(work, seed, 128, thresh=0)
        patch = work.point(lambda v: 255 if v == 128 else 0)
        if patch.histogram()[255] >= min_area:
            keep.paste(255, (0, 0), patch)
        ImageDraw.floodfill(work, seed, 0, thresh=0)

    return keep


# Share of the frame's outer band that must match the regenerated vignette
# before the plate is treated as one this tool matted. Every matted character
# scores 69% or better; art that arrived on a plain matte instead scores 0.
_VIGNETTE_BORDER_MIN = 0.40


def _backdrop_for(im: Image.Image, vignette: Image.Image) -> Image.Image:
    """The colour field sitting behind the character, ready to be subtracted.

    Usually that is the vignette this tool painted in, reproduced exactly.
    Some art never went through that step and arrived on a plain flat matte
    instead; there the backdrop is simply that colour, read off the frame's
    own border. Either way the caller gets a picture of "what is behind", so
    the alpha and un-mixing maths downstream does not care which it was.
    """
    import numpy as np

    rgb = np.asarray(im.convert("RGB"), np.float32)
    vig = np.asarray(vignette.convert("RGB"), np.float32)
    h, w = rgb.shape[:2]
    band = max(2, min(h, w) // 80)
    ring = np.zeros((h, w), bool)
    ring[:band, :] = ring[-band:, :] = ring[:, :band] = ring[:, -band:] = True

    matches = (np.abs(rgb - vig).max(axis=2)[ring] <= _DEMATTE_TOLERANCE).mean()
    if matches >= _VIGNETTE_BORDER_MIN:
        return vignette
    flat = tuple(int(v) for v in np.median(rgb[ring], axis=0))
    return Image.new("RGB", im.size, flat)


def _dematte_frame(im: Image.Image, vignette: Image.Image) -> Image.Image:
    """Turn a vignette-backed plate into an RGBA cutout of just the character.

    `matte_all` replaced the generator's checkerboard with an opaque vignette,
    which is why a character reads as a rectangle pasted over the scene rather
    than as a figure standing in it. JPEG cannot hold alpha, so the backdrop
    had to be *some* colour — but the colour it was given is reproducible, so
    it can be identified exactly and lifted back out.

    Because the old backdrop B is known per pixel, the edge needs no guessing
    either. A boundary pixel is O = a*F + (1-a)*B, so once alpha is known the
    character's own colour comes back as F = (O - (1-a)*B) / a. That is what
    removes the dark fringe, rather than eroding the silhouette until the
    fringe is gone and the character's outline with it.
    """
    import numpy as np   # authoring-only; not a runtime dependency of the API

    rgb = np.asarray(im.convert("RGB"), np.float32)
    bg = np.asarray(_backdrop_for(im, vignette).convert("RGB"), np.float32)

    distance = np.abs(rgb - bg).max(axis=2)
    candidates = Image.fromarray(
        np.where(distance <= _DEMATTE_TOLERANCE, 255, 0).astype(np.uint8), "L"
    )
    background = _confirm_background(candidates)

    # Clean the silhouette while it is still a hard mask — feathering first
    # would only smear the crumbs into faint smudges instead of removing them.
    solid = _drop_specks(background.point(lambda v: 255 - v))

    # Anti-alias the cut without rounding off pixel-art corners: a sub-pixel
    # blur softens only the boundary pixel and leaves a hard edge hard.
    alpha = solid.filter(ImageFilter.GaussianBlur(0.6))
    a = np.asarray(alpha, np.float32)[..., None] / 255.0

    # Un-mix the backdrop out of the partly transparent boundary pixels.
    safe = np.maximum(a, 1e-3)
    foreground = np.clip((rgb - (1.0 - a) * bg) / safe, 0, 255)
    # Fully transparent pixels keep the character's colour rather than the
    # vignette's, so a viewer that ignores alpha shows no dark rectangle and
    # scaling never drags backdrop colour back in along the edge.
    foreground = np.where(a > 0, foreground, rgb)

    out = np.concatenate([foreground, a * 255.0], axis=2)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def dematte_all(characters_dir: Path = CHARACTERS_DIR) -> list:
    """Give every matted character frame real transparency, as PNG.

    Rewrites frame_N.jpg as frame_N.png and drops the JPEG, so the frame map
    the frontend builds from the directory picks the cutouts up with no
    change on its side. Idempotent via the `.matted` marker, which is
    replaced by `.dematted`.
    """
    if not characters_dir.is_dir():
        return []

    log = []
    for folder in sorted(characters_dir.rglob("*")):
        if not folder.is_dir():
            continue
        frames = sorted(folder.glob("frame_*.jpg"), key=_frame_index)
        if not frames or (folder / ".dematted").exists():
            continue

        with Image.open(frames[0]) as probe:
            vignette = _make_vignette(probe.size)

        for frame in frames:
            with Image.open(frame) as im:
                cutout = _dematte_frame(im, vignette)
            cutout.save(frame.with_suffix(".png"))
            frame.unlink()

        (folder / ".matted").unlink(missing_ok=True)
        (folder / ".dematted").touch()
        log.append(
            f"{folder.relative_to(characters_dir)}: {len(frames)} frame(s) -> RGBA png"
        )

    return log


# ---------------------------------------------------------------------------
# Putting a folder's frames back on one canvas
# ---------------------------------------------------------------------------
#
# Art arrives cropped frame by frame, each PNG trimmed to its own drawing, so
# `warden` alone spans 522x519 down to 472x505. The frontend draws a character
# with `background-size: contain`, which fits every frame to *its own* box: a
# narrower frame is scaled up more, and the figure jumps in size and sideways
# on every swap. No CSS fixes that, because what the trimming threw away —
# where each drawing sat on the canvas the artist worked on — is not in the
# file any more.
#
# It is recoverable. Consecutive frames of one loop are the same drawing with
# small changes, so the offset that best re-overlaps two frames is the offset
# the trim removed. Phase correlation over the alpha masks finds it in one FFT
# per frame, and every frame is matched against frame 1 directly, so error
# cannot accumulate along a long loop. On the art in this repo, mask overlap
# with frame 1 rises from 0.30-0.77 to 0.72-0.99.

# Correlate at this size rather than full resolution. The residual is one
# probe pixel, i.e. ~2px on a 2000px sprite — well under a screen pixel once
# the frame is fitted to the viewport, and it keeps a 2200x2067 folder from
# building four 70MB float planes.
_REGISTER_PROBE = 1024


def _frames_in(folder: Path) -> list:
    """Every image in `folder`, in the order the frontend will play them."""
    return sorted(
        (p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS),
        key=_frame_index,
    )


def _alpha_plane(im: Image.Image, shape: tuple, scale: float):
    """One frame's alpha, shrunk by `scale` and zero-padded to `shape`."""
    import numpy as np

    alpha = im.getchannel("A")
    if scale < 1:
        alpha = alpha.resize(
            (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        )
    mask = np.asarray(alpha, dtype=np.float32) / 255.0
    plane = np.zeros(shape, np.float32)
    plane[: mask.shape[0], : mask.shape[1]] = mask
    return plane


def _register_offsets(frames: list) -> list:
    """(dx, dy) per frame, placing each drawing where frame 1 has it."""
    import numpy as np

    # Padded to twice the largest frame so a shift can never wrap around the
    # correlation and come back reading as its own opposite.
    span_x = max(f.width for f in frames) * 2
    span_y = max(f.height for f in frames) * 2
    scale = min(1.0, _REGISTER_PROBE / max(span_x, span_y))
    shape = (max(1, round(span_y * scale)), max(1, round(span_x * scale)))

    anchor = np.fft.rfft2(_alpha_plane(frames[0], shape, scale))
    offsets = [(0, 0)]
    for frame in frames[1:]:
        power = anchor * np.conj(np.fft.rfft2(_alpha_plane(frame, shape, scale)))
        peak = np.fft.irfft2(power, shape)
        dy, dx = np.unravel_index(int(np.argmax(peak)), shape)
        # The peak index runs 0..n; anything past the halfway point is a
        # negative shift that has wrapped to the far end of the axis.
        dy = dy - shape[0] if dy > shape[0] // 2 else dy
        dx = dx - shape[1] if dx > shape[1] // 2 else dx
        offsets.append((round(dx / scale), round(dy / scale)))
    return offsets


def _on_common_canvas(frames: list, offsets: list) -> list:
    """Each frame pasted at its offset onto one canvas that holds them all."""
    left = min(dx for dx, _ in offsets)
    top = min(dy for _, dy in offsets)
    width = max(dx + f.width for f, (dx, _) in zip(frames, offsets)) - left
    height = max(dy + f.height for f, (_, dy) in zip(frames, offsets)) - top

    placed = []
    for frame, (dx, dy) in zip(frames, offsets):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(frame, (dx - left, dy - top))
        placed.append(canvas)
    return placed


def register_all(characters_dir: Path = CHARACTERS_DIR) -> list:
    """Align every character folder's frames onto one shared canvas, in place.

    Idempotent via a `.registered` marker; delete it to re-run a folder after
    dropping new art in.
    """
    if not characters_dir.is_dir():
        return []

    log = []
    for folder in sorted(characters_dir.rglob("*")):
        if not folder.is_dir() or (folder / ".registered").exists():
            continue

        paths = _frames_in(folder)
        # A frame that never finished copying is a blank flash in the loop,
        # not a frame. Drop it rather than animate a broken image.
        for empty in [p for p in paths if p.stat().st_size == 0]:
            empty.unlink()
            paths.remove(empty)
            log.append(f"{folder.relative_to(characters_dir)}: dropped empty {empty.name}")
        if len(paths) < 2:
            continue

        frames = [Image.open(p).convert("RGBA") for p in paths]
        placed = _on_common_canvas(frames, _register_offsets(frames))
        for path, frame in zip(paths, placed):
            frame.save(path.with_suffix(".png"))
            if path.suffix.lower() != ".png":
                path.unlink()

        (folder / ".registered").touch()
        log.append(
            f"{folder.relative_to(characters_dir)}: {len(paths)} frame(s) aligned "
            f"on {placed[0].width}x{placed[0].height}"
        )

    return log


# ---------------------------------------------------------------------------
# Cutting art that still carries its placeholder checkerboard.
#
# This is the path for art delivered as PNG, and it is strictly better than
# `_dematte_frame` above — that one exists only to rescue the JPEG plates
# already in the repo, whose checkerboard was destroyed by compression.
#
# Why a checkerboard is the *good* case. For a partly transparent pixel,
#
#     O = a*F + (1 - a)*B
#
# A flat backdrop gives one equation and two unknowns, so a glow or a
# feathered wing can only be guessed at. A checkerboard gives two backdrop
# values, and subtracting the two cases eliminates F entirely:
#
#     D          = O - B = a*(F - B)
#     D_light - D_dark   = -a*(B_light - B_dark)
#
# So the placeholder's own ripple, still visible through a semi-transparent
# region, states that region's alpha outright:
#
#     a = |local ripple of D| / (B_light - B_dark)
#
# Measured against synthetic ground truth in `demo()`: mean alpha error
# 0.02, and under 0.004 where the art is fully transparent.
# ---------------------------------------------------------------------------

# The ripple has to be measured over a window holding both checker phases.
# Tested at 0.5x to 3x the cell size, 2x is the clear optimum: smaller windows
# miss a phase and read noise, larger ones smear the alpha gradient.
_RIPPLE_WINDOW_CELLS = 2
# How close to 0 or 1 an averaged alpha must land before it is taken to mean
# exactly clear or exactly solid. Tested at 0.06 / 0.10 / 0.15: 0.06 gives the
# cleanest empty frame without eating into a genuine soft edge.
_ALPHA_SNAP = 0.06


def _box_mean(plane, size: int):
    """Mean over a size x size window, via a summed-area table.

    A box blur does not justify a scipy dependency in an authoring script that
    otherwise needs only numpy and Pillow.
    """
    import numpy as np

    radius = size // 2
    padded = np.pad(plane, radius, mode="edge")
    table = np.pad(padded.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    h, w = plane.shape
    y0, x0 = np.mgrid[0:h, 0:w]
    y1, x1 = y0 + size, x0 + size
    total = table[y1, x1] - table[y0, x1] - table[y1, x0] + table[y0, x0]
    return total / float(size * size)


def detect_checkerboard(rgb, probe: int = 8):
    """Read the placeholder's geometry off the frame border.

    Returns (pitch, phase_y, phase_x, tone_lo, tone_hi). The outer band of a
    generated sheet is always pure placeholder, so the runs of constant colour
    along it give the cell size and where the grid starts. Verified exact on
    randomised pitch, phase and tones in `demo()`.
    """
    import numpy as np

    grey = rgb.mean(axis=2)
    h, w = grey.shape
    band = np.concatenate([
        grey[:probe, :].ravel(), grey[-probe:, :].ravel(),
        grey[:, :probe].ravel(), grey[:, -probe:].ravel(),
    ])
    values, counts = np.unique(band.round(2), return_counts=True)
    pair = values[np.argsort(counts)[-2:]]
    lo, hi = float(min(pair)), float(max(pair))

    def first_run(line):
        nearer_hi = np.abs(line - hi) < np.abs(line - lo)
        edges = np.flatnonzero(np.diff(nearer_hi.astype(np.int8)) != 0) + 1
        return edges

    edges = first_run(grey[1])
    if len(edges) >= 2:
        pitch = max(2, int(round(float(np.median(np.diff(edges))))))
        phase_x = int(edges[0] % pitch)
    else:
        pitch, phase_x = 16, 0
    down = first_run(grey[:, 1])
    phase_y = int(down[0] % pitch) if len(down) else 0
    return pitch, phase_y, phase_x, lo, hi


def _checker_plate(h: int, w: int, pitch: int, phase_y: int, phase_x: int,
                   lo: float, hi: float):
    import numpy as np

    yy, xx = np.mgrid[0:h, 0:w]
    parity = (((yy - phase_y) // pitch) + ((xx - phase_x) // pitch)) % 2
    grey = np.where(parity == 0, hi, lo).astype(np.float32)
    return np.repeat(grey[..., None], 3, axis=2), parity


def cut_from_checkerboard(im: Image.Image) -> Image.Image:
    """Turn a checkerboard-backed plate into an RGBA cutout.

    Unlike the vignette path, no threshold is chosen and nothing is eroded:
    alpha is *measured* from the placeholder showing through, so a glow fades
    out exactly as drawn instead of being cut off at whatever cutoff happened
    to be tuned.
    """
    import numpy as np

    rgb = np.asarray(im.convert("RGB"), np.float32)
    h, w = rgb.shape[:2]
    pitch, phase_y, phase_x, lo, hi = detect_checkerboard(rgb)
    if hi - lo < 4:                      # no usable placeholder contrast
        raise ValueError("no checkerboard detected — is this art already cut?")

    plate, parity = _checker_plate(h, w, pitch, phase_y, phase_x, lo, hi)
    # Orient the model to the art: a disagreeing corner means inverted parity.
    py, px = min(phase_y + 1, h - 1), min(phase_x + 1, w - 1)
    if abs(rgb[py, px].mean() - plate[py, px].mean()) > (hi - lo) / 2:
        grey = np.where(parity == 0, lo, hi).astype(np.float32)
        plate = np.repeat(grey[..., None], 3, axis=2)

    residual = (rgb - plate).mean(axis=2)
    sign = np.where(parity == 0, 1.0, -1.0).astype(np.float32)
    ripple = 2.0 * _box_mean(residual * sign, _RIPPLE_WINDOW_CELLS * pitch)
    alpha = np.clip(np.abs(ripple) / (hi - lo), 0.0, 1.0)

    # The ripple is averaged over a window, so it lands a little short of the
    # extremes: empty frame reads as 0.02 rather than 0, a solid body as 0.97
    # rather than 1. Snapping both ends is what the art actually means, and it
    # cuts the error over transparent regions by roughly five times.
    alpha = np.where(alpha < _ALPHA_SNAP, 0.0,
                     np.where(alpha > 1.0 - _ALPHA_SNAP, 1.0, alpha))

    a = alpha[..., None]
    # Un-mix the placeholder back out. Below the floor the pixel is so nearly
    # transparent that dividing would only amplify noise into a bright fringe.
    safe = np.maximum(a, 0.05)
    fore = np.clip((rgb - (1.0 - a) * plate) / safe, 0, 255)
    fore = np.where(a > 0.05, fore, rgb)
    out = np.concatenate([fore, a * 255.0], axis=2)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


# --- Cutting placeholder-backed art that has been through JPEG -------------
#
# `cut_from_checkerboard` above measures alpha from the placeholder's ripple,
# which needs the grid to be pixel-exact. JPEG smears it: the cell edges blur,
# the two tones drift, and the phase wanders across the frame. Run on the
# shipped sheets it keeps barely 1% of the frame as transparent, against the
# ~60% actually there.
#
# What survives compression is cruder but solid — the placeholder is *grey*
# and sits at one of *two brightnesses*. Keying on that pair, rather than on
# the geometry, is what these files support.
#
# Anything more saturated than this is drawn, not placeholder. Measured across
# the refurbished sheets: placeholder chroma sits at 0-5, and the least
# saturated real costume (the warden's steel) clears 34.
_PLACEHOLDER_CHROMA_MAX = 26.0
# How far from a tone still counts as that tone, as a share of their gap.
_PLACEHOLDER_TONE_FRAC = 0.35
# Below this the backdrop is one flat colour, not a checkerboard.
_MIN_TONE_GAP = 12.0
# ...and below this the two "tones" are really backdrop versus art, so the
# backdrop is flat however wide the split looks. Real checkerboards score 43%+
# here; the one flat plate in the set scores 2%.
_MIN_TONE_BALANCE = 0.20


def _placeholder_tones(rgb, border: int = 24) -> tuple:
    """(tone_lo, tone_hi, balance) of the placeholder, read off the frame border.

    Two-means rather than percentiles: the split has to land between the tones
    wherever they happen to sit, and the generator has used pairs as far apart
    as 90/180 and as close as 1/39.

    `balance` is the share of the border falling in the smaller of the two
    groups. A checkerboard alternates, so its two tones come out near even —
    43% to 50% across every sheet here. A flat backdrop has no second tone, so
    two-means splits the backdrop against whatever art touches the frame and
    the minority collapses: the riddle weaver's plate scores 2%. Gap alone
    cannot tell those apart — her split reads as a *wider* gap than any real
    checkerboard — so the caller has to check the balance too.
    """
    import numpy as np

    grey = rgb.mean(axis=2)
    h, w = grey.shape
    ring = np.zeros((h, w), bool)
    ring[:border, :] = ring[-border:, :] = ring[:, :border] = ring[:, -border:] = True
    band = grey[ring]

    lo, hi = np.percentile(band, 10), np.percentile(band, 90)
    for _ in range(30):
        near_lo = band[np.abs(band - lo) <= np.abs(band - hi)]
        near_hi = band[np.abs(band - lo) > np.abs(band - hi)]
        if len(near_lo):
            lo = near_lo.mean()
        if len(near_hi):
            hi = near_hi.mean()

    share = float((np.abs(band - lo) <= np.abs(band - hi)).mean())
    return float(min(lo, hi)), float(max(lo, hi)), min(share, 1.0 - share)


def cut_placeholder(im: Image.Image) -> Image.Image:
    """Cut a character off its generated backdrop, checkerboard or flat.

    Handles both because the generator has produced both: most sheets carry
    the two-tone checkerboard, while the riddle weaver's arrived on a single
    flat blue-grey plate.
    """
    import numpy as np

    rgb = np.asarray(im.convert("RGB"), np.float32)
    grey = rgb.mean(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    lo, hi, balance = _placeholder_tones(rgb)
    checkered = (hi - lo) >= _MIN_TONE_GAP and balance >= _MIN_TONE_BALANCE

    if checkered:
        tolerance = max(6.0, (hi - lo) * _PLACEHOLDER_TONE_FRAC)
        distance = np.minimum(np.abs(grey - lo), np.abs(grey - hi))
        candidate = (distance < tolerance) & (chroma < _PLACEHOLDER_CHROMA_MAX)
        plate_colour = (lo + hi) / 2.0
    else:
        # Flat backdrop: key on the whole colour, since a single grey level
        # cannot be told from a grey costume by brightness alone.
        h, w = grey.shape
        ring = np.zeros((h, w), bool)
        ring[:24, :] = ring[-24:, :] = ring[:, :24] = ring[:, -24:] = True
        flat = np.median(rgb[ring], axis=0)
        candidate = np.abs(rgb - flat).max(axis=2) < 26.0
        tolerance, plate_colour = 26.0, float(flat.mean())

    confirmed = _confirm_background(
        Image.fromarray(np.where(candidate, 255, 0).astype(np.uint8), "L")
    )
    solid = _drop_specks(confirmed.point(lambda v: 255 - v))
    alpha = np.asarray(solid, np.float32) / 255.0

    # A glow drawn over the placeholder keeps some of it showing through, so
    # those pixels read as part-grey and part-tone. Fading them by how much
    # placeholder remains lets a halo taper out instead of ending on the square
    # edges of whichever checker cells happened to clear the threshold.
    if checkered:
        greyness = np.clip(1.0 - chroma / _PLACEHOLDER_CHROMA_MAX, 0, 1)
        near_tone = np.clip(
            1.0 - np.minimum(np.abs(grey - lo), np.abs(grey - hi)) / (tolerance * 2.0),
            0, 1,
        )
        alpha = np.clip(alpha * (1.0 - 0.85 * greyness * near_tone), 0, 1)

    alpha = np.asarray(
        Image.fromarray((alpha * 255).astype(np.uint8), "L")
        .filter(ImageFilter.GaussianBlur(0.8)),
        np.float32,
    )[..., None] / 255.0

    plate = np.full_like(rgb, plate_colour)
    safe = np.maximum(alpha, 0.05)
    fore = np.clip((rgb - (1.0 - alpha) * plate) / safe, 0, 255)
    fore = np.where(alpha > 0.05, fore, rgb)
    return Image.fromarray(
        np.concatenate([fore, alpha * 255.0], axis=2).astype(np.uint8), "RGBA"
    )


def cut_sheet(sheet: Path, out_dir: Path, start_index: int = 1) -> int:
    """Split one 2x2 placeholder-backed sheet into frame_N.png cutouts.

    Returns the next free frame index, so a character shipped as two sheets
    (the dragon) continues the numbering instead of overwriting itself.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    index = start_index
    with Image.open(sheet) as im:
        im = im.convert("RGB")
        for box in _quadrant_boxes(im):
            cut_from_checkerboard(im.crop(box)).save(out_dir / f"frame_{index}.png")
            index += 1
    return index


def demo() -> None:
    """Self-check: slicing a synthetic 2x2 sheet yields 4 correctly-cropped
    square frames, in reading order. Run: python -m app.engine.sprite_slicer --selfcheck"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sheet = tmp / "combo.jpg"
        im = Image.new("RGB", (100, 100))
        px = im.load()
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        for y in range(100):
            for x in range(100):
                quadrant = (1 if x >= 50 else 0) + (2 if y >= 50 else 0)
                px[x, y] = colors[quadrant]
        im.save(sheet)

        out = tmp / "out"
        next_i = _slice_sheet(sheet, out)
        assert next_i == 5
        frames = sorted(out.glob("frame_*.jpg"))
        assert len(frames) == 4, frames

        with Image.open(out / "frame_1.jpg") as f1:
            assert f1.size == (50, 50)
            assert f1.getpixel((25, 25))[0] > 200  # top-left: red
        with Image.open(out / "frame_3.jpg") as f3:
            assert f3.getpixel((25, 25))[2] > 200  # bottom-left: blue

    # _replace_checkerboard: a red "ring" (standing in for a coiled dragon's
    # body) sits on a grey checkerboard field. The ring encloses a large
    # pocket of that same checkerboard -- never touching the frame's edge --
    # and also has a small grey detail (a buckle) embedded in its own body.
    # Expected: border checkerboard AND the large enclosed pocket both
    # become vignette; the ring's own colour and the small buckle survive.
    size = (120, 120)
    im = Image.new("RGB", size)
    px = im.load()
    for y in range(120):
        for x in range(120):
            block_is_light = ((x // 10) + (y // 10)) % 2 == 0
            px[x, y] = (200, 200, 200) if block_is_light else (100, 100, 100)

    ring_thickness = 15
    for y in range(10, 110):
        for x in range(10, 110):
            on_ring = (
                x < 10 + ring_thickness or x >= 110 - ring_thickness
                or y < 10 + ring_thickness or y >= 110 - ring_thickness
            )
            if on_ring:
                px[x, y] = (220, 40, 40)      # the "character": saturated red

    for y in range(15, 22):
        for x in range(50, 57):
            px[x, y] = (150, 150, 150)        # small detail embedded in the ring, e.g. a buckle

    vignette = Image.new("RGB", size, (0, 0, 255))  # unmistakable stand-in colour
    out = _replace_checkerboard(im, vignette)

    outer_bg = out.getpixel((2, 2))
    assert outer_bg[2] > 200 and outer_bg[0] < 50, outer_bg          # touches border -> vignette
    ring = out.getpixel((17, 60))
    assert ring[0] > 150 and ring[2] < 100, ring                     # the ring itself, untouched
    buckle = out.getpixel((53, 18))
    assert max(buckle) - min(buckle) < 10, buckle                    # small enclosed detail survives
    inner_pocket = out.getpixel((60, 60))
    assert inner_pocket[2] > 200 and inner_pocket[0] < 50, inner_pocket  # large enclosed pocket -> vignette too

    # A 2x2 sheet with a ruled divider: every quadrant must come back free of
    # the divider, and all four the same size, or the location would flicker
    # and resize as the frontend cycles through its frames.
    import random
    for divider in ((0, 0, 0), (255, 255, 255)):
        sheet_im = Image.new("RGB", (200, 200))
        sp = sheet_im.load()
        random.seed(7)
        for y in range(200):
            for x in range(200):
                sp[x, y] = (random.randrange(60, 200), random.randrange(40, 180),
                            random.randrange(30, 160))
        ImageDraw.Draw(sheet_im).rectangle([0, 97, 200, 102], fill=divider)
        ImageDraw.Draw(sheet_im).rectangle([97, 0, 102, 200], fill=divider)

        assert _find_divider(sheet_im) == ((97, 103), (97, 103))
        cut = [sheet_im.crop(b) for b in _quadrant_boxes(sheet_im)]
        assert len({c.size for c in cut}) == 1, [c.size for c in cut]
        for quadrant in cut:
            assert _line_std(quadrant.convert("L").crop(
                (0, quadrant.height - 1, quadrant.width, quadrant.height)
            )) >= _DIVIDER_STD_MAX, "divider survived into a quadrant"

    # ...and a single scene must survive untouched.
    assert _find_divider(sheet_im.crop((0, 0, 97, 97))) is None

    # De-matting: a red disc on a known backdrop comes back as a clean cutout —
    # opaque disc, transparent surround, and no backdrop colour smeared into
    # the rim. Both backdrop kinds are covered: the vignette this tool paints,
    # and the flat matte some art arrives on.
    for backdrop in ("vignette", "flat"):
        size = (120, 120)
        field = _make_vignette(size) if backdrop == "vignette" \
            else Image.new("RGB", size, (125, 145, 156))
        plate = field.copy()
        ImageDraw.Draw(plate).ellipse([35, 35, 84, 84], fill=(220, 30, 30))

        cutout = _dematte_frame(plate, _make_vignette(size))
        assert cutout.mode == "RGBA"
        assert cutout.getpixel((60, 60))[3] == 255, backdrop      # disc is opaque
        assert cutout.getpixel((4, 4))[3] == 0, backdrop          # surround is clear
        rim = cutout.getpixel((60, 37))                           # top of the disc
        assert rim[0] > rim[1] + 60 and rim[0] > rim[2] + 60, (backdrop, rim)

    # --- checkerboard cutting, against synthetic ground truth ---------------
    # A known alpha map is composited over a known checkerboard, then recovered.
    # This is the only way to check a matte honestly: on real art there is
    # nothing to compare the answer to.
    import numpy as np

    for pitch, phase, tones in [(16, (0, 0), (102.0, 153.0)),
                                (8, (3, 5), (120.0, 190.0)),
                                (32, (7, 11), (140.0, 175.0))]:
        lo, hi = tones
        size = 256
        plate, parity = _checker_plate(size, size, pitch, phase[0], phase[1], lo, hi)

        yy, xx = np.mgrid[0:size, 0:size]
        radius = np.hypot(yy - size / 2, xx - size / 2)
        truth = np.clip((70 - radius) / 10.0, 0, 1)                  # solid body
        truth = np.maximum(truth, np.clip((110 - radius) / 60.0, 0, 1) * 0.5)  # glow

        fore = np.zeros((size, size, 3), np.float32)
        fore[..., 0], fore[..., 1], fore[..., 2] = 205, 95, 235
        obs = truth[..., None] * fore + (1 - truth[..., None]) * plate

        found = detect_checkerboard(obs)
        assert found[0] == pitch, (pitch, found)
        assert abs(found[3] - lo) < 1.5 and abs(found[4] - hi) < 1.5, (tones, found)

        cut = np.asarray(cut_from_checkerboard(
            Image.fromarray(obs.astype(np.uint8), "RGB")), np.float32)
        got = cut[..., 3] / 255.0
        error = np.abs(got - truth)
        clear = truth < 0.02
        assert error.mean() < 0.07, (pitch, float(error.mean()))
        assert error[clear].mean() < 0.01, (pitch, float(error[clear].mean()))

    # --- frame registration -------------------------------------------------
    # Two crops of the same drawing, trimmed differently, must come back the
    # same size with the drawing in the same place. That is the whole contract:
    # if it holds, `background-size: contain` scales every frame identically
    # and the figure stops jumping between frames.
    art = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(art).ellipse([120, 90, 200, 210], fill=(30, 200, 120, 255))
    crops = [art.crop((100, 70, 260, 250)), art.crop((60, 40, 230, 260))]

    placed = _on_common_canvas(crops, _register_offsets(crops))
    assert len({p.size for p in placed}) == 1, [p.size for p in placed]
    boxes = [p.getbbox() for p in placed]
    assert max(abs(a - b) for a, b in zip(*boxes)) <= 2, boxes

    # A frame that is genuinely a different drawing must not be dragged onto
    # the first one — a zero shift stays zero.
    same = [art.copy(), art.copy()]
    assert _register_offsets(same) == [(0, 0), (0, 0)], _register_offsets(same)

    print("sprite_slicer: self-check passed")


REFURBISHED_DIR = REPO_ROOT / "assets" / "characetrs_refurbished"

# Which uncut sheet feeds which character folder. The delivered filenames do
# not all match the folder names the .scene files already reference, and one
# arrived with the generator's default name, so the mapping is written out
# rather than guessed from the filename.
REFURBISHED_SHEETS = {
    "alchemist": ["alchemist.jpg"],
    "cataloguer": ["cataloguer.jpg"],
    "crystal": ["crystal.jpg"],
    "dragon": ["dragon.jpg", "dragon_2.jpg"],          # eight frames, two sheets
    "elder_mage": ["elder_mage.jpg"],
    "enchanter": ["enchanter.jpg"],
    "mysterious_figure": ["mysterious_figure.jpg"],
    "player/female": ["female_player.jpg"],
    "player/male": ["male_player.jpg"],
    "quartermaster": ["quarter_master.jpg"],
    "riddle_weaver": ["riddleweaver.jpg"],
    "system": ["system.jpg"],
    # Identified by eye against the shipped frames: purple robe, white beard,
    # open book with floating runes — the Sage, not the elder mage.
    "system_sage": ["Generated Image July 26, 2026 - 11_50PM (1).jpg"],
    "warden": ["warden.jpg"],
}


def refurbish_all(source: Path = REFURBISHED_DIR,
                  characters_dir: Path = CHARACTERS_DIR) -> list:
    """Re-cut every character from its uncut sheet, replacing the old frames.

    One pass from the original art beats the shipped two-step (checkerboard to
    vignette, vignette back to alpha), which had to guess a threshold twice and
    left speckle and haloing behind.
    """
    log = []
    for name, sheets in REFURBISHED_SHEETS.items():
        present = [source / s for s in sheets if (source / s).is_file()]
        if not present:
            log.append(f"{name}: SKIPPED — no source sheet found")
            continue

        out_dir = characters_dir / name
        out_dir.mkdir(parents=True, exist_ok=True)
        for stale in list(out_dir.glob("frame_*.png")) + list(out_dir.glob("frame_*.jpg")):
            stale.unlink()

        index = 1
        for sheet in present:
            with Image.open(sheet) as im:
                im = im.convert("RGB")
                for box in _quadrant_boxes(im):
                    cut_placeholder(im.crop(box)).save(out_dir / f"frame_{index}.png")
                    index += 1
        (out_dir / ".matted").unlink(missing_ok=True)
        (out_dir / ".dematted").write_text("cut from placeholder\n", encoding="utf-8")
        log.append(f"{name}: {index - 1} frame(s) from {len(present)} sheet(s)")
    return log


INCOMING_DIR = REPO_ROOT / "art_prompts" / "incoming"

# Which character each incoming sheet belongs to, and in what order. A
# character shipped as two sheets (the dragon's eight frames) lists both, and
# the frames are numbered straight through.
SHEET_SETS = {
    "dragon": ["dragon_sheet_1.png", "dragon_sheet_2.png"],
    "mysterious_figure": ["mysterious_figure_sheet.png"],
}


def cut_incoming(incoming: Path = INCOMING_DIR,
                 characters_dir: Path = CHARACTERS_DIR) -> list:
    """Cut every placeholder-backed sheet in `incoming` into character frames.

    Replaces that character's frames outright — this path produces strictly
    better cutouts than the JPEG rescue above, so there is nothing to keep.
    """
    log = []
    for name, sheets in SHEET_SETS.items():
        present = [incoming / s for s in sheets if (incoming / s).is_file()]
        if not present:
            continue

        out_dir = characters_dir / name
        for stale in list(out_dir.glob("frame_*.png")) + list(out_dir.glob("frame_*.jpg")):
            stale.unlink()

        index = 1
        for sheet in present:
            index = cut_sheet(sheet, out_dir, index)
        (out_dir / ".matted").unlink(missing_ok=True)
        (out_dir / ".dematted").write_text("cut from checkerboard\n", encoding="utf-8")
        log.append(f"{name}: {index - 1} frame(s) from {len(present)} sheet(s)")
    return log


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        demo()
    elif "--refurbish" in sys.argv:
        for line in refurbish_all():
            print(f"[sprite_slicer] {line}")
    elif "--register" in sys.argv:
        for line in register_all():
            print(f"[sprite_slicer] {line}")
    elif "--cut-incoming" in sys.argv:
        lines = cut_incoming()
        for line in lines:
            print(f"[sprite_slicer] {line}")
        if not lines:
            print(f"[sprite_slicer] no sheets found in {INCOMING_DIR}")
    else:
        sliced = slice_all()
        for line in sliced:
            print(f"[sprite_slicer] {line}")
        matted = matte_all()
        for line in matted:
            print(f"[sprite_slicer] {line}")
        # Last, because it wants the final PNGs: whatever the frames came from,
        # they only animate cleanly once they share a canvas.
        registered = register_all()
        for line in registered:
            print(f"[sprite_slicer] {line}")
        if not sliced and not matted and not registered:
            print("[sprite_slicer] nothing to do - already up to date")
