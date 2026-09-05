import { useEffect, useRef } from 'react';

/**
 * Enter or Space advances the story.
 *
 * Clicking through a whole chapter on a trackpad is what makes long scenes
 * feel like work, so every "Continue" beat — dialogue, System panel, reward,
 * finished interaction — answers to the keyboard as well.
 *
 * The callback lives in a ref so the listener binds once and still calls this
 * render's closure; a dep array would either go stale or re-bind constantly.
 */
export default function useAdvanceKey(onAdvance, enabled = true) {
  const latest = useRef(onAdvance);
  latest.current = onAdvance;

  useEffect(() => {
    if (!enabled) return undefined;
    const onKey = (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      // Never steal the key from a field being typed in, nor from a focused
      // button — the browser already turns Enter there into a click, and
      // handling it here too would advance two beats at once.
      if (e.target?.closest?.('input, textarea, button, a, [contenteditable="true"]')) return;
      e.preventDefault();
      latest.current?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled]);
}
