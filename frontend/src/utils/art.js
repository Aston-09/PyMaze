import { apiFetch } from './api';

// The {stem: [frame paths]} map plus the list of which stems are character
// cutouts. Identical for the whole session, so fetch once and share the
// promise across every consumer.
let artPromise = null;

export function loadArt() {
  if (!artPromise) {
    artPromise = apiFetch('/backgrounds/frames')
      .then((r) => (r.ok ? r.json() : null))
      // Tolerate the older shape (a bare frame map) so a stale backend still
      // renders locations, just without character stacking.
      .then((d) => (d?.frames ? d : { frames: d || {}, characters: [] }))
      .catch(() => ({ frames: {}, characters: [] }));
  }
  return artPromise;
}

/** The set of stems that are character cutouts rather than locations. */
export function loadCharacterStems() {
  return loadArt().then((d) => new Set(d.characters || []));
}
