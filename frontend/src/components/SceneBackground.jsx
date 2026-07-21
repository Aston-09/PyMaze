import React, { useState, useEffect, useRef } from 'react';

import { ASSET_URL as ASSET_BASE } from '../config';

const ASSET_URL = `${ASSET_BASE}/backgrounds`;

/**
 * Choose how an image meets the frame.
 *
 * The rule is categorical rather than a distance threshold, deliberately.
 * Most scene art here is square (1024x1024), which sits almost exactly on any
 * reasonable numeric tolerance — so a threshold would flip those images
 * between filling and letterboxing on a mere window resize.
 *
 * Instead: only art that is genuinely *portrait* on a *landscape* screen gets
 * contained. That is the case where cropping to fill destroys the subject —
 * the celestial dragon is 768x1376, and `cover` on a widescreen monitor shows
 * a narrow horizontal band of its chest with the whole dragon lost.
 *
 * Everything else fills the frame, stably, at every window size.
 */
function chooseFit(imageWidth, imageHeight) {
  const image = imageWidth / imageHeight;
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
 * 1. **Mixed aspect ratios.** Scene art is landscape; character art is
 *    portrait. Rather than crop one to fit the other, each image is measured
 *    on load: images close to the viewport's shape fill it edge to edge,
 *    while tall or narrow ones are shown whole against a blurred, scaled-up
 *    copy of themselves. The subject is always visible.
 *
 * 2. **Stillness.** A static plate reads as a screenshot. Every layer drifts,
 *    each new location pushes in with its own entrance, and a slow field of
 *    motes moves across the whole frame.
 *
 * Props:
 *   src: background filename from the .scene, or null for none
 */
export default function SceneBackground({ src }) {
  const [layers, setLayers] = useState([]);   // [{ src, key, fit }]
  const counter = useRef(0);

  useEffect(() => {
    if (!src) {
      setLayers([]);
      return;
    }

    let cancelled = false;

    // Measure before showing, so the image never appears in the wrong fit
    // and then visibly snap to the right one.
    const decide = (fit) => {
      if (cancelled) return;
      counter.current += 1;
      const next = { src, key: counter.current, fit };
      setLayers((prev) => {
        if (prev[prev.length - 1]?.src === src) return prev;
        return [...prev.slice(-1), next];   // keep outgoing + incoming only
      });
    };

    const probe = new Image();
    probe.onload = () => decide(chooseFit(probe.naturalWidth, probe.naturalHeight));
    // A failed probe should still show the image rather than a blank screen.
    probe.onerror = () => decide('cover');
    probe.src = `${ASSET_URL}/${encodeURIComponent(src)}`;

    return () => { cancelled = true; };
  }, [src]);

  if (!layers.length) return null;

  return (
    <div className="scene-background" aria-hidden="true">
      {layers.map((layer, i) => {
        const url = `url("${ASSET_URL}/${encodeURIComponent(layer.src)}")`;
        const state = i === layers.length - 1 ? 'is-current' : 'is-outgoing';
        return (
          <div key={layer.key} className={`scene-plate ${state} fit-${layer.fit}`}>
            {/* Blurred backdrop fills the frame whenever the sharp image
                cannot; harmless (and hidden) when it can. */}
            <div className="scene-plate-fill" style={{ backgroundImage: url }} />
            <div className="scene-plate-image" style={{ backgroundImage: url }} />
          </div>
        );
      })}

      <div className="scene-motes" />
      <div className="scene-background-scrim" />
    </div>
  );
}
