import React, { useState } from 'react';
import Editor from '@monaco-editor/react';

import { apiFetch } from '../utils/api';

/**
 * Monaco styled as ink on vellum, so the editor reads as part of the page
 * rather than a black rectangle pasted onto it.
 */
const PARCHMENT_THEME = {
  base: 'vs',
  inherit: true,
  rules: [
    { token: '', foreground: '2f2418', background: 'f8f1e0' },
    { token: 'comment', foreground: '9a866b', fontStyle: 'italic' },
    { token: 'string', foreground: '2f4f6b' },
    { token: 'number', foreground: '8a6420' },
    { token: 'keyword', foreground: '97372b', fontStyle: 'bold' },
    { token: 'identifier', foreground: '2f2418' },
    { token: 'delimiter', foreground: '6b5842' },
  ],
  colors: {
    'editor.background': '#f8f1e0',
    'editor.foreground': '#2f2418',
    'editorLineNumber.foreground': '#bda580',
    'editorLineNumber.activeForeground': '#8a6420',
    'editor.selectionBackground': '#e0cfa8',
    'editor.lineHighlightBackground': '#f2e8d2',
    'editorCursor.foreground': '#2f2418',
    'editorIndentGuide.background': '#e6d8b8',
    'editorIndentGuide.activeBackground': '#d4c39c',
  },
};

/**
 * ChallengePanel — code editor, instructions and results ledger.
 *
 * Props:
 *   challenge: the challenge definition from the API (already player-rendered)
 *   onSuccess: called with the execution result when the challenge passes
 */
export default function ChallengePanel({ challenge, onSuccess }) {
  const [code, setCode] = useState(challenge?.starting_code || '');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  // Learner failure recovery: tracks whether the challenge has been passed
  const [passed, setPassed] = useState(false);

  const executeCode = async () => {
    setExecuting(true);
    setResult(null);

    try {
      const response = await apiFetch(`/execute`, {
        method: 'POST',
        body: JSON.stringify({ code, challenge_id: challenge.challenge_id }),
      });
      const data = await response.json();
      setResult(data);

      if (data.success || data.trial_failed) {
        // Mark as passed so the UI changes to "Continue"
        setPassed(true);
        // Let the verdict land before the scene moves on.
        setTimeout(() => onSuccess?.(data), 1200);
      }
      // On failure: do NOT auto-advance. The learner stays on the challenge
      // and can edit their code and retry.
    } catch {
      setResult({
        success: false,
        message: 'Network error. Is the backend running?',
        test_results: [],
      });
    } finally {
      setExecuting(false);
    }
  };

  const handleRetry = () => {
    // Clear the failed result so the learner can try again with a clean slate
    setResult(null);
  };

  if (!challenge) return null;

  const hasFailed = result && !result.success && !passed;

  return (
    <>
      {/* Left page: the quest as written */}
      <div className="panel challenge-panel-instructions">
        <h2>{challenge.title}</h2>
        <div className="panel-content">
          <div className="narrative-box">{challenge.narrative}</div>

          <h3>Instructions</h3>
          <ul className="instruction-list">
            {challenge.instructions.split('\n').map((line, i) =>
              line.trim() ? <li key={i}>{line.replace(/^- /, '')}</li> : null
            )}
          </ul>

          {challenge.hints?.length > 0 && (
            <>
              <h3>Hints</h3>
              <ul className="instruction-list">
                {challenge.hints.map((hint, i) => (
                  <li key={i} style={{ color: 'var(--ink-soft)', fontSize: '0.92rem' }}>{hint}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Right page: the working slip */}
      <div className="panel challenge-panel-editor">
        <div className="challenge-editor-header">
          <h3 style={{ margin: 0 }}>Your Code</h3>
          <button className="btn btn-primary" onClick={executeCode} disabled={executing || passed}>
            {executing ? (
              <><div className="loading-spinner" style={{ width: 14, height: 14 }} /> Casting…</>
            ) : passed ? 'Passed ✓' : 'Cast the Spell'}
          </button>
        </div>

        <div className="editor-container">
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="pymaze-parchment"
            value={code}
            onChange={(val) => setCode(val || '')}
            beforeMount={(monaco) => {
              monaco.editor.defineTheme('pymaze-parchment', PARCHMENT_THEME);
            }}
            options={{
              minimap: { enabled: false },
              fontSize: 15,
              fontFamily: "'Fira Code', monospace",
              fontLigatures: false,
              padding: { top: 16 },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              renderLineHighlight: 'line',
              readOnly: passed,
            }}
          />
        </div>

        {/* Results ledger — sticky footer */}
        <div className="challenge-results-footer">
          <div className="output-terminal">
            <div className="output-header">
              <span>Result</span>
              {result && (
                <span className={`status-badge ${result.success ? 'status-success' : 'status-error'}`}>
                  {result.success ? 'Passed' : 'Failed'}
                </span>
              )}
            </div>

            {result ? (
              <div>
                <p className={`output-message ${result.success ? 'is-success' : 'is-error'}`}>
                  {result.message}
                </p>

                {result.test_results?.length > 0 && (
                  <div>
                    {result.test_results.map((t) => (
                      <div key={t.test_id} className={`test-result ${t.passed ? 'test-pass' : 'test-fail'}`}>
                        <strong>Test {t.test_id}:</strong> {t.input} →{' '}
                        {t.passed ? 'as expected' : `Expected: ${t.expected} | Got: ${t.actual || t.error}`}
                      </div>
                    ))}
                  </div>
                )}

                {result.output && (
                  <div className="output-stream">
                    <pre>{result.output}</pre>
                  </div>
                )}

                {/* Retry button: only for learner failures, not for passed/trial_failed */}
                {hasFailed && (
                  <div className="challenge-retry-area">
                    <button className="btn btn-primary" onClick={handleRetry}>
                      Try Again
                    </button>
                    <span className="challenge-retry-hint">Edit your code above and cast again.</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="output-placeholder">
                Write your code, then cast it to see what the world answers.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
