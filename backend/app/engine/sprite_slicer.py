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

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

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


def _slice_sheet(sheet: Path, out_dir: Path, start_index: int = 1) -> int:
    """Split one 2x2 contact sheet into 4 square frame_N files.

    Reading order matches how the generator lays out a 4-panel sheet:
    left-to-right, top-to-bottom (frame_1 = top-left ... frame_4 = bottom-
    right). Returns the next free frame index, so a second sheet for the
    same character (the dragon ships two) continues the sequence instead of
    overwriting it.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(sheet) as im:
        im = im.convert("RGB")
        w, h = im.size
        hw, hh = w // 2, h // 2
        boxes = [(0, 0, hw, hh), (hw, 0, w, hh), (0, hh, hw, h), (hw, hh, w, h)]
        for i, box in enumerate(boxes):
            im.crop(box).save(out_dir / f"frame_{start_index + i}.jpg", quality=92)
    return start_index + len(boxes)


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
    w, h = im.size
    min_area = max(80, int(w * h * _MIN_BACKGROUND_FRACTION))

    saturation = im.convert("HSV").split()[1]
    working = saturation.point(lambda v: 255 if v <= _SAT_THRESHOLD else 0)

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

    confirmed = working.point(lambda v: 255 if v == BACKGROUND else 0)
    confirmed = confirmed.filter(ImageFilter.GaussianBlur(1.5))  # soften the cut edge

    return Image.composite(vignette, im, confirmed)


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
