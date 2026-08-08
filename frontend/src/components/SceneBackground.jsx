import React, { useState, useEffect, useRef } from 'react';

import { ASSET_URL } from '../config';
import { apiFetch } from '../utils/api';

const FRAME_MS = 2600;   // how long each frame holds before cross-fading to the next

// The {stem: [frame paths]} map is the same for the whole session, so fetch it
// once and share the promise across every SceneBackground mount. It covers
// both location folders (backgrounds/ancient_library/...) and character
// portraits (characters/warden/..., characters/player/male/...) — see
// backend `_art_frame_map()`. A `background:` tag in a .scene file doesn't
// care which one it names; both animate the same way.
let framesMapPromise = null;
function loadFramesMap() {
  if (!framesMapPromise) {
    framesMapPromise = apiFetch('/backgrounds/frames')
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({}));
  }
  return framesMapPromise;
}

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

// Where the art lives says what it is. Character folders hold transparent
// cutouts meant to stand in a location; background folders hold the location
// itself. The .scene file just names a stem either way.
function isCharacter(frames) {
  return frames[0]?.startsWith('characters/');
}

// encodeURIComponent per segment so "stem/frame_1.jpg" keeps its slash but a
// stray space or paren in a loose filename is still escaped.
function frameUrl(relPath) {
  return `${ASSET_URL}/${relPath.split('/').map(encodeURIComponent).join('/')}`;
}

/**
 * Choose how an image meets the frame.
 *
 * Locations are 16:9 and always fill edge to edge (`cover`) — that is what
 * a scene painting is for. Character portraits are boxy (512x512, a
 * centered cutout with room around it) and always want the opposite: shown
 * whole (`contain`), floating over their own blurred backdrop. `cover` on a
 * boxy sprite zooms into its center and can slice a head or feet clean off,
 * and there is no viewport shape where that becomes correct — so this is a
 * fixed property of the art's own proportions, not the window's, and it
 * never flips mid-session the way a viewport-relative check would.
 *
 * Between those two: art that is genuinely *portrait* on a *landscape*
 * screen also gets contained — cropping to fill would destroy the subject
 * (the celestial dragon is 768x1376; `cover` on a widescreen monitor shows a
 * narrow band of its chest with the whole dragon lost). Everything else
 * fills the frame, stably, at every window size.
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
 * SceneBackground — the world behind the page.
 *
 * Two problems this solves:
 *
 * 1. **Mixed aspect ratios.** Scene art is landscape; character portraits are
 *    boxy cutouts. Rather than crop one to fit the other, each image is
 *    measured on load: art close to the viewport's shape fills it edge to
 *    edge, while boxy or narrow art is shown whole against a blurred,
 *    scaled-up copy of itself. The subject is always visible.
 *
 * 2. **Stillness.** A static plate reads as a screenshot. Every layer drifts,
 *    each new location pushes in with its own entrance, and a slow field of
 *    motes moves across the whole frame.
 *
 * Props:
 *   src: a `background:` ref from the .scene — a location filename (e.g.
 *        "valley_vista.jpg") or a character stem (e.g. "warden", resolved
 *        server-side from "player" to the learner's chosen sprite) — or
 *        null for none.
 */
export default function SceneBackground({ src }) {
  const [layers, setLayers] = useState([]);   // [{ src, key, fit }] — the place
  const [cutout, setCutout] = useState(null); // the character standing in it
  const counter = useRef(0);

  useEffect(() => {
    if (!src) {
      setLayers([]);
      setCutout(null);
      return;
    }

    let cancelled = false;
    let timer = null;

    // Measure before showing, so the image never appears in the wrong fit
    // and then visibly snap to the right one.
    // `enter` distinguishes a new location (pushes in) from a frame swap within
    // the same location (a plain cross-fade — no zoom, so the scene doesn't throb).
    const push = (relPath, enter) => {
      counter.current += 1;
      const key = counter.current;
      const show = (fit) => {
        if (cancelled) return;
        const next = { src: relPath, key, fit, enter };
        setLayers((prev) => {
          if (prev[prev.length - 1]?.src === relPath) return prev;
          return [...prev.slice(-1), next];   // keep outgoing + incoming only
        });
      };
      const probe = new Image();
      probe.onload = () => show(chooseFit(probe.naturalWidth, probe.naturalHeight));
      // A failed probe should still show the image rather than a blank screen.
      probe.onerror = () => show('cover');
      probe.src = frameUrl(relPath);
    };

    loadFramesMap().then((map) => {
      if (cancelled) return;
      const frames = framesFor(src, map);
      let i = 0;

      // A character is a cutout with real transparency, so it goes *in* the
      // place rather than replacing it: the location keeps playing underneath
      // and only this top layer changes. A location swaps the plates as before.
      if (isCharacter(frames)) {
        setCutout({ src: frames[0], key: (counter.current += 1) });
        if (frames.length > 1) {
          timer = setInterval(() => {
            i = (i + 1) % frames.length;
            setCutout((prev) => (prev ? { ...prev, src: frames[i] } : prev));
          }, FRAME_MS);
        }
        return;
      }

      setCutout(null);
      push(frames[0], true);
      // More than one frame → drift the location by cross-fading through them.
      if (frames.length > 1) {
        timer = setInterval(() => {
          i = (i + 1) % frames.length;
          push(frames[i], false);
        }, FRAME_MS);
      }
    });

    return () => { cancelled = true; if (timer) clearInterval(timer); };
  }, [src]);

  if (!layers.length) return null;

  return (
    <div className="scene-background" aria-hidden="true">
      {layers.map((layer, i) => {
        const url = `url("${frameUrl(layer.src)}")`;
        const current = i === layers.length - 1;
        const state = current ? 'is-current' : 'is-outgoing';
        const enter = current && layer.enter ? ' is-enter' : '';
        return (
          <div key={layer.key} className={`scene-plate ${state} fit-${layer.fit}${enter}`}>
            {/* Blurred backdrop fills the frame whenever the sharp image
                cannot; harmless (and hidden) when it can. */}
            <div className="scene-plate-fill" style={{ backgroundImage: url }} />
            <div className="scene-plate-image" style={{ backgroundImage: url }} />
          </div>
        );
      })}

      {/* Above the place, below the air and the grade — so the character is
          lit and toned by the same pass as everything behind them. */}
      {cutout && (
        <div
          key={cutout.key}
          className="scene-character"
          style={{ backgroundImage: `url("${frameUrl(cutout.src)}")` }}
        />
      )}

      <div className="scene-motes" />
      <div className="scene-background-scrim" />
    </div>
  );
}
