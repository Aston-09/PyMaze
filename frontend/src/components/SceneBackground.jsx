import React, { useEffect, useState } from 'react';

import { ASSET_URL } from '../config';
import { loadArt } from '../utils/art';

// A location is a flipbook. Four drawings of one place, cut hard from one to
// the next — no fade, no zoom, nothing tweened. 800ms a frame is a 3.2s
// cycle: slow enough to sit under text somebody is reading, so the place
// shifts rather than flickers. Anything softer *between* frames would turn
// the cels into a dissolve and the place would stop looking drawn.
const PLACE_FRAME_MS = 800;

// A character is the same reel run slow: long enough for a pose to be read
// while its dialogue is on screen, and blended rather than cut so a speaking
// figure does not twitch under the text.
const FIGURE_FRAME_MS = 2000;

// Someone who has asked the system for less motion gets a still plate. The
// reduced-motion block in index.css cannot reach this: a reel is a timer, not
// an animation, so neutering animation-duration leaves it cutting frames on
// its own — which is most of what that setting exists to prevent.
const stillness = window.matchMedia('(prefers-reduced-motion: reduce)');

// The {stem: [frame paths]} map covers both location folders
// (backgrounds/ancient_library/...) and character portraits
// (characters/warden/..., characters/player/male/...) — see backend
// `_art_frame_map()`. What differs is only that a character is drawn *over* a
// location rather than instead of it.

// A scene's `background: ancient_library.png` (a place) or `background:
// warden` (a character's own art) becomes the ordered list of animation
// frames wherever that stem's folder actually lives, already resolved to
// full paths relative to /assets by the backend. A stem with no folder
// falls back to its single loose file under backgrounds/.
function framesFor(src, map) {
  const stem = src.replace(/\.[^.]+$/, '');
  const frames = map[stem];
  if (frames && frames.length) return frames;
  return [`backgrounds/${src}`];
}

// encodeURIComponent per segment so "stem/frame_1.jpg" keeps its slash but a
// stray space or paren in a loose filename is still escaped.
function frameUrl(relPath) {
  return `${ASSET_URL}/${relPath.split('/').map(encodeURIComponent).join('/')}`;
}

/**
 * Choose how an image meets the frame.
 *
 * Locations are 16:9 and always fill edge to edge (`cover`) — that is what a
 * scene painting is for. Character portraits are boxy (a centered cutout with
 * room around it) and always want the opposite: shown whole (`contain`),
 * floating over their own blurred backdrop. `cover` on a boxy sprite zooms
 * into its center and can slice a head or feet clean off, and there is no
 * viewport shape where that becomes correct — so this is a fixed property of
 * the art's own proportions, not the window's, and it never flips mid-session
 * the way a viewport-relative check would.
 *
 * Between those two: art that is genuinely *portrait* on a *landscape* screen
 * also gets contained — cropping to fill would destroy the subject.
 * Everything else fills the frame, stably, at every window size.
 */
function chooseFit(imageWidth, imageHeight) {
  const image = imageWidth / imageHeight;

  const boxyArt = image > 0.85 && image < 1.15;
  if (boxyArt) return 'contain';

  const view = window.innerWidth / window.innerHeight;
  const portraitArt = image < 0.95;
  const landscapeScreen = view > 1.2;
  return portraitArt && landscapeScreen ? 'contain' : 'cover';
}

/**
 * Fetch and decode one frame. Resolves to the Image, or null if it 404s.
 *
 * `decode()` finishes the job `onload` only starts: onload means the bytes
 * arrived, decode means the bitmap is ready to paint. A frame still being
 * decoded when its turn comes paints as a blank flash, so the reel waits for
 * all of them before it starts.
 */
function frameReady(url) {
  const image = new Image();
  const arrived = new Promise((resolve) => {
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
  });
  image.src = url;
  return arrived.then((ok) => (
    ok && image.decode ? image.decode().then(() => image, () => image) : ok
  ));
}

/**
 * Play one art folder as a flipbook.
 *
 * Returns `{ urls, fit, index, under, pinned }` once every frame is decoded,
 * or null before that. Nothing is drawn from a half-loaded reel, and when the
 * stem changes the previous reel keeps playing until the new one is ready — a
 * swap is a cut, never a gap.
 *
 * `under` is the frame the reel just left, or -1 on the very first one. It is
 * counted from a running tick rather than wrapped backwards from `index`,
 * because those disagree exactly once and it is the once that shows: wrapping
 * would make the last frame of the reel the predecessor of the first, so a
 * character would fade in as two drawings at once on the way in.
 *
 * `pinned` holds the decoded Image objects, only so the browser cannot evict
 * a frame it has stopped painting and then re-fetch it mid-loop.
 */
function useReel(stem, frameMs) {
  const [reel, setReel] = useState(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!stem) {
      setReel(null);
      return undefined;
    }
    let cancelled = false;

    loadArt().then(({ frames: map }) => {
      if (cancelled) return undefined;
      const urls = framesFor(stem, map).map(frameUrl);
      return Promise.all(urls.map(frameReady)).then((pinned) => {
        if (cancelled) return;
        // The fit is measured once per folder rather than once per frame:
        // every frame of a reel now shares one canvas (sprite_slicer
        // `register_all`), so one measurement is the truth for all of them.
        const measured = pinned.find((img) => img && img.naturalWidth);
        setTick(0);
        setReel({
          stem,
          urls,
          pinned,
          fit: measured
            ? chooseFit(measured.naturalWidth, measured.naturalHeight)
            : 'cover',
        });
      });
    });

    return () => { cancelled = true; };
  }, [stem]);

  useEffect(() => {
    if (!reel || reel.urls.length < 2) return undefined;
    let beat = null;
    // Re-read on change rather than once, so the setting takes hold on the
    // scene already on screen instead of the next one.
    const follow = () => {
      clearInterval(beat);
      beat = null;
      if (stillness.matches) setTick(0);
      else beat = setInterval(() => setTick((n) => n + 1), frameMs);
    };
    follow();
    stillness.addEventListener('change', follow);
    return () => {
      clearInterval(beat);
      stillness.removeEventListener('change', follow);
    };
  }, [reel, frameMs]);

  // Wrapping here rather than in the tick keeps the count honest across a reel
  // swap: a long reel replaced by a short one can never index off the end.
  return reel && {
    ...reel,
    index: tick % reel.urls.length,
    under: tick === 0 ? -1 : (tick - 1) % reel.urls.length,
  };
}

/**
 * SceneBackground — the world behind the page.
 *
 * The art is drawn frame by frame, so the animation is the frames and nothing
 * else: each reel is cut through in order and looped, with no motion
 * synthesised on top of it. Both reels are paced to be read under narration
 * rather than watched: a location cuts every 800ms, a character holds well
 * past that and blends instead of cutting.
 *
 * Mixed aspect ratios are the one thing still measured at runtime: scene art
 * is landscape, character portraits are boxy cutouts. Rather than crop one to
 * fit the other, each reel is measured on load — art close to the viewport
 * shape fills it edge to edge, while boxy or narrow art is shown whole
 * against a blurred, scaled-up copy of itself.
 *
 * Props:
 *   src:       the location — a `background:` ref naming a place (e.g.
 *              "valley_vista.jpg"), or null for none.
 *   character: who is standing in it — a character stem (e.g. "warden", or
 *              "player" resolved server-side to the chosen sprite), or null.
 *              Drawn over `src`, never in place of it.
 */
export default function SceneBackground({ src, character }) {
  const place = useReel(src, PLACE_FRAME_MS);
  const figure = useReel(character, FIGURE_FRAME_MS);

  if (!place && !figure) return null;

  return (
    <div className="scene-background" aria-hidden="true">
      {/* The place. One layer, its image swapped outright — a hard cut is the
          whole point, and every frame is decoded and pinned before the reel
          starts, so a swap costs a repaint and nothing else. Keyed by stem, so
          arriving somewhere new replays the fade-up on the container while
          frame swaps within one location leave the container alone. */}
      {place && (
        <div key={place.stem} className={`scene-plate fit-${place.fit}`}>
          {/* Blurred backdrop, visible only where the sharp image leaves gaps.
              Held on the first frame: it is blurred past recognition, so
              re-rasterising it every frame would buy nothing. */}
          <div
            className="scene-plate-fill"
            style={{ backgroundImage: `url("${place.urls[0]}")` }}
          />
          <div
            className="scene-plate-image"
            style={{ backgroundImage: `url("${place.urls[place.index]}")` }}
          />
        </div>
      )}

      {/* Above the place, below the air and the grade — so the character is
          lit and toned by the same pass as everything behind them.

          Stacked rather than swapped, because this reel blends. The outgoing
          frame is held opaque underneath while the incoming one fades in over
          it; fading both at once would leave the figure see-through through
          the middle of every swap, with the location showing straight through
          them. Depth comes from z-index rather than document order, because
          the reel wraps and frame 1 has to come out on top of frame 4. */}
      {figure && (
        <div key={figure.stem} className="scene-character">
          {figure.urls.map((url, n) => {
            const showing = n === figure.index;
            const lit = showing || n === figure.under;
            return (
              <div
                key={url}
                className={`scene-character-frame${lit ? ' is-lit' : ''}`}
                style={{ backgroundImage: `url("${url}")`, zIndex: showing ? 2 : 1 }}
              />
            );
          })}
        </div>
      )}

      <div className="scene-motes" />
      <div className="scene-background-scrim" />
    </div>
  );
}
