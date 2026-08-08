"""
Sprite Sheet Slicer

Authoring tool, not part of the running engine: splits a combined 2x2
"contact sheet" image — the shape the art generator hands back when asked
for a 4-frame idle loop — into separate frame_N files under the same folder,
so the frontend's existing frame-cycling code (built for background
locations) animates character portraits too, with no code change per
character.

It then mattes each frame: every portrait was generated on a "flat/
transparent background", but the source files are JPEG, which cannot hold
real alpha — so the generator baked its transparency placeholder in as a
literal grey-and-white checkerboard. Left alone, that checkerboard would
fill the whole screen behind every character. This swaps it for a soft
vignette instead, classifying each connected patch of checkerboard-like
pixels by size: a small patch (a grey belt buckle, a silver armor plate)
is left alone regardless of where it sits, while a large patch is treated
as background even if a coiled tail or a spread wing fully encloses it and
it never touches the frame's edge.

Run after dropping new art into assets/characters/<name>/:
    python -m app.engine.sprite_slicer

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

    print("sprite_slicer: self-check passed")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        demo()
    else:
        sliced = slice_all()
        for line in sliced:
            print(f"[sprite_slicer] {line}")
        matted = matte_all()
        for line in matted:
            print(f"[sprite_slicer] {line}")
        if not sliced and not matted:
            print("[sprite_slicer] nothing to do - already up to date")
