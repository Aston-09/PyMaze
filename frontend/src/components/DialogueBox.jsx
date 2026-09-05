import React, { useState, useEffect, useRef, useCallback } from 'react';

/**
 * DialogueBox — RPG-style typewriter dialogue renderer.
 *
 * Characters are shown through the scene background rather than as cut-out
 * portraits, so this component only ever draws the speaker's nameplate.
 *
 * Props:
 *   dialogues: Array of { speaker, lines }
 *   onComplete: called when all dialogue has been shown
 *   onSkipAll: called when the player wants to skip all dialogue in the scene
 */
export default function DialogueBox({ dialogues, onComplete, onSkipAll }) {
  const [currentDialogueIdx, setCurrentDialogueIdx] = useState(0);
  const [currentLineIdx, setCurrentLineIdx] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const timerRef = useRef(null);

  const currentDialogue = dialogues[currentDialogueIdx];
  const currentLine = currentDialogue?.lines[currentLineIdx] || '';

  // Typewriter effect
  useEffect(() => {
    if (!currentLine) return;

    setDisplayedText('');
    setIsTyping(true);
    let charIdx = 0;

    timerRef.current = setInterval(() => {
      charIdx++;
      setDisplayedText(currentLine.slice(0, charIdx));
      if (charIdx >= currentLine.length) {
        clearInterval(timerRef.current);
        setIsTyping(false);
      }
    }, 28);

    return () => clearInterval(timerRef.current);
  }, [currentDialogueIdx, currentLineIdx, currentLine]);

  const handleContinue = useCallback(() => {
    // If still typing, complete instantly
    if (isTyping) {
      clearInterval(timerRef.current);
      setDisplayedText(currentLine);
      setIsTyping(false);
      return;
    }

    // Move to next line in current dialogue
    if (currentLineIdx < currentDialogue.lines.length - 1) {
      setCurrentLineIdx(prev => prev + 1);
      return;
    }

    // Move to next dialogue block
    if (currentDialogueIdx < dialogues.length - 1) {
      setCurrentDialogueIdx(prev => prev + 1);
      setCurrentLineIdx(0);
      return;
    }

    // All done
    onComplete?.();
  }, [isTyping, currentLine, currentLineIdx, currentDialogue, currentDialogueIdx, dialogues.length, onComplete]);

  // Keyboard: Enter/Space advances dialogue.
  // Scoped to this component — only fires when no input/textarea/editor is focused.
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;

      // Don't fire when the user is typing in an input, textarea, or code editor
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      // Monaco editor uses a textarea internally with a specific class
      if (document.activeElement?.closest('.monaco-editor')) return;
      // Don't steal from contentEditable elements
      if (document.activeElement?.isContentEditable) return;

      e.preventDefault();
      handleContinue();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleContinue]);

  if (!currentDialogue) return null;

  // Speaker → nameplate colour. Matched on substring so "System Sage" and
  // "???" (the Sage before he lowers his hood) read as one voice.
  const name = currentDialogue.speaker.toLowerCase();
  const speakerClass =
    name === 'narrator' ? 'narrator'
    : name.includes('sage') || name === '???' ? 'sage'
    : name.includes('system') ? 'system'
    : name.includes('dragon') ? 'dragon'
    : '';

  return (
    <div className="dialogue-container slide-up">
      <div className="dialogue-box">
        <div className={`dialogue-speaker ${speakerClass}`}>
          {currentDialogue.speaker}
        </div>
        <div className="dialogue-text">
          {displayedText}
          {isTyping && <span className="dialogue-cursor" />}
        </div>
        <div className="dialogue-controls">
          {onSkipAll && (
            <button className="btn btn-ghost" onClick={onSkipAll} style={{ opacity: 0.7, marginRight: 'auto' }}>
              Skip Scene ⏭
            </button>
          )}
          <button className="btn btn-ghost" onClick={handleContinue}>
            {isTyping ? 'Skip ⏩' : (
              currentDialogueIdx >= dialogues.length - 1 &&
              currentLineIdx >= currentDialogue.lines.length - 1
            ) ? 'Continue →' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
}
