import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import DialogueBox from './DialogueBox';
import ChallengePanel from './ChallengePanel';
import RewardPopup from './RewardPopup';
import DragonOverlay from './DragonOverlay';
import EndScreen from './EndScreen';
import InteractionStage from './interactions/InteractionStage';
import SceneBackground from './SceneBackground';
import { loadCharacterStems } from '../utils/art';
import SystemPanel from './SystemPanel';

import { apiFetch } from '../utils/api';

/**
 * Collapse a scene's beat stream into playable segments.
 *
 * Consecutive dialogue beats become one segment so prose still flows under a
 * single "Next", while interactions and missions each stand alone. This is
 * what lets a chapter teach → play → teach → test inside one scene.
 */
function toSegments(beats = [], characterStems = new Set()) {
  const segments = [];
  // `background:` is scenery, not a step the player clicks through. It names
  // either a *place* or a *character*, and the two stack rather than replace:
  // `background: ruins.png` then `background: warden` means the warden is
  // standing in the ruins. Treating them as one slot is what made every
  // character beat wipe the location and leave the speaker floating in black.
  let place = null;
  let character = null;

  const stemOf = (ref) => ref.replace(/\.[^.]+$/, '');
  const here = () => ({ background: place, character });

  for (const beat of beats) {
    const last = segments[segments.length - 1];

    if (beat.type === 'background') {
      if (characterStems.has(stemOf(beat.ref))) {
        character = beat.ref;
      } else {
        // A new location clears whoever was standing in the old one.
        place = beat.ref;
        character = null;
      }
    } else if (beat.type === 'dialogue') {
      // Merge into the running dialogue block, unless the scenery just
      // changed — a new place or a new speaker on stage deserves its own reveal.
      if (last?.kind === 'dialogue' && last.background === place && last.character === character) {
        last.dialogues.push({ speaker: beat.speaker, lines: beat.lines });
      } else {
        segments.push({
          kind: 'dialogue',
          ...here(),
          dialogues: [{ speaker: beat.speaker, lines: beat.lines }],
        });
      }
    } else if (beat.type === 'system') {
      // Always its own segment — a System panel interrupts, by design.
      segments.push({ kind: 'system', ...here(), ref: beat.ref, lines: beat.lines });
    } else if (beat.type === 'interactive') {
      segments.push({ kind: 'interactive', ...here(), ref: beat.ref });
    } else if (beat.type === 'mission') {
      segments.push({ kind: 'mission', ...here(), ref: beat.ref });
    } else if (beat.type === 'choice') {
      segments.push({ kind: 'choice', ...here(), options: beat.options || [] });
    }
  }

  return segments;
}

export default function SceneManager({ player, setPlayer }) {
  const [mode, setMode] = useState('loading');
  const [scene, setScene] = useState(null);
  const [segmentIdx, setSegmentIdx] = useState(0);
  const [rewardData, setRewardData] = useState(null);
  const [dragonData, setDragonData] = useState(null);
  const [pendingNextScene, setPendingNextScene] = useState(null);
  // What to re-attempt from the error screen: {what: 'scene'|'advance', sceneId}.
  const [retry, setRetry] = useState(null);

  // Which art stems are character cutouts. Fetched once and shared; until it
  // arrives every ref reads as a location, which is the old behaviour.
  const [characterStems, setCharacterStems] = useState(null);
  useEffect(() => { loadCharacterStems().then(setCharacterStems); }, []);

  const segments = useMemo(
    () => toSegments(scene?.beats, characterStems || new Set()),
    [scene, characterStems],
  );
  const segment = segments[segmentIdx];

  // What is actually on screen. Compared against the player's `current_scene`
  // below so the same scene is never fetched twice.
  const loadedScene = useRef(null);

  const fetchScene = useCallback(async (sceneId) => {
    try {
      loadedScene.current = sceneId;
      setMode('loading');
      const res = await apiFetch(`/scene/${sceneId}`);
      if (!res.ok) {
        // A scene that genuinely does not exist is a content bug and the run is
        // over; anything else (server restart, dropped connection, a 500) is
        // temporary and must be retryable. Collapsing both to "end" is what
        // made a blip look like the game finishing mid-chapter.
        if (res.status === 404) {
          setMode('end');
        } else {
          loadedScene.current = null;
          setRetry({ what: 'scene', sceneId });
          setMode('error');
        }
        return;
      }
      const data = await res.json();
      setScene(data);
      setSegmentIdx(0);
      setMode(data.beats?.length ? 'playing' : 'end');
    } catch (err) {
      console.error('Failed to fetch scene:', err);
      loadedScene.current = null;
      setRetry({ what: 'scene', sceneId });
      setMode('error');
    }
  }, []);

  // Load whatever scene the player is standing in — on mount, and again if
  // something outside this component moves them. `advanceToScene` already
  // fetched the scene it moved to, so re-fetching on that same player update
  // would duplicate the request and tear down the Dragon's Judgment overlay
  // mid-play. The guard means this only fires on a genuine jump.
  useEffect(() => {
    const target = player?.current_scene;
    if (target && target !== loadedScene.current) {
      fetchScene(target);
    }
  }, [player?.current_scene, fetchScene]);


  const advanceToScene = useCallback(async (currentSceneId) => {
    try {
      setMode('loading');
      const res = await apiFetch(`/advance`, {
        method: 'POST',
        body: JSON.stringify({ current_scene: currentSceneId }),
      });
      // Without this, an error body parses fine, yields no `current_scene`,
      // and the run silently "ends" in the middle of a chapter.
      if (!res.ok) {
        setRetry({ what: 'advance', sceneId: currentSceneId });
        setMode('error');
        return;
      }
      const data = await res.json();
      if (data.player) setPlayer(data.player);

      // The Dragon's Judgment plays over the transition out of the encounter.
      if (data.dragon_judgment) {
        setDragonData(data.dragon_judgment);
        setPendingNextScene(data.current_scene || null);
        setMode('dragon');
        return;
      }

      if (data.current_scene) {
        fetchScene(data.current_scene);
      } else {
        setMode('end');
      }
    } catch (err) {
      console.error('Failed to advance:', err);
      setRetry({ what: 'advance', sceneId: currentSceneId });
      setMode('error');
    }
  }, [fetchScene, setPlayer]);

  /** Take a `choice:` branch, saving it so a reload lands on the chosen path. */
  const chooseScene = useCallback(async (target) => {
    if (!scene?.scene_id) return;
    try {
      setMode('loading');
      const res = await apiFetch(`/advance`, {
        method: 'POST',
        body: JSON.stringify({ current_scene: scene.scene_id, chosen_scene: target }),
      });
      if (!res.ok) {
        setRetry({ what: 'scene', sceneId: target });
        setMode('error');
        return;
      }
      const data = await res.json();
      if (data.player) setPlayer(data.player);
      fetchScene(data.current_scene || target);
    } catch (err) {
      console.error('Failed to take choice:', err);
      setRetry({ what: 'scene', sceneId: target });
      setMode('error');
    }
  }, [scene, fetchScene, setPlayer]);

  /** Move to the next segment, or leave the scene once the stream runs out. */
  const nextSegment = useCallback(() => {
    if (segmentIdx < segments.length - 1) {
      setSegmentIdx((i) => i + 1);
      setMode('playing');
    } else if (scene?.scene_id) {
      advanceToScene(scene.scene_id);
    } else {
      setMode('end');
    }
  }, [segmentIdx, segments.length, scene, advanceToScene]);

  /** Skip all dialogues to the next task, system panel, or end of scene. */
  const skipToNextTask = useCallback(() => {
    let nextIdx = segmentIdx + 1;
    while (nextIdx < segments.length) {
      const k = segments[nextIdx].kind;
      if (k === 'mission' || k === 'interactive' || k === 'system') {
        break;
      }
      nextIdx++;
    }

    if (nextIdx < segments.length) {
      setSegmentIdx(nextIdx);
      setMode('playing');
    } else if (scene?.scene_id) {
      advanceToScene(scene.scene_id);
    } else {
      setMode('end');
    }
  }, [segmentIdx, segments, scene, advanceToScene]);

  const handleChallengeSuccess = (result) => {
    if (result.player) setPlayer(result.player);

    if (result.trial_failed) {
      fetchScene('chapter_1_trial_failed');
      return;
    }

    const challenge = scene?.challenges?.[segment?.ref];
    setRewardData({
      reward: challenge?.reward || {},
      statBonuses: result.stat_bonuses || {},
    });
    setMode('reward');
  };

  const handleDragonDismiss = () => {
    if (pendingNextScene) {
      fetchScene(pendingNextScene);
      setPendingNextScene(null);
    } else {
      setMode('end');
    }
  };

  if (mode === 'loading') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <div className="loading-spinner" style={{ width: 40, height: 40 }} />
      </div>
    );
  }

  // A stumble on the way to the next beat used to look identical to finishing
  // the game. The player's progress is already saved server-side, so the only
  // thing lost is this hop — offer it back rather than ending the run.
  if (mode === 'error') {
    return (
      <div className="main-content" style={{ gridTemplateColumns: '1fr' }}>
        <div className="panel" style={{ maxWidth: 460, margin: 'auto', textAlign: 'center' }}>
          <h2>The path flickers</h2>
          <p>Something went wrong reaching the next moment. Your progress is safe.</p>
          <button
            className="btn btn-primary"
            onClick={() => {
              if (!retry) return;
              if (retry.what === 'advance') advanceToScene(retry.sceneId);
              else fetchScene(retry.sceneId);
            }}
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (mode === 'end') return <EndScreen player={player} />;

  const challenge = segment?.kind === 'mission' ? scene?.challenges?.[segment.ref] : null;
  const interaction = segment?.kind === 'interactive' ? scene?.interactions?.[segment.ref] : null;

  // The world is shown behind narration only. Coding and puzzle beats keep a
  // clean page so nothing competes with the work. System panels keep it too —
  // they read as an overlay on the world, so the world stays visible.
  const showBackground = segment?.kind === 'dialogue' || segment?.kind === 'system' || segment?.kind === 'choice';

  return (
    <>
      {showBackground && (
        <SceneBackground src={segment.background} character={segment.character} />
      )}

      {mode === 'playing' && segment?.kind === 'dialogue' && (
        <div className="main-content" style={{ gridTemplateColumns: '1fr' }}>
          <div className="narration-frame">
            <DialogueBox
              key={segmentIdx}
              dialogues={segment.dialogues}
              onComplete={nextSegment}
              onSkipAll={skipToNextTask}
            />
          </div>
        </div>
      )}

      {mode === 'playing' && segment?.kind === 'system' && (
        <div className="main-content" style={{ gridTemplateColumns: '1fr' }}>
          <SystemPanel
            key={segmentIdx}
            variant={segment.ref}
            lines={segment.lines}
            onComplete={nextSegment}
          />
        </div>
      )}

      {mode === 'playing' && segment?.kind === 'choice' && (
        <div className="main-content" style={{ gridTemplateColumns: '1fr' }}>
          <div className="narration-frame">
            <div className="dialogue-container slide-up">
              <div className="dialogue-box">
                <div className="dialogue-speaker">Your choice</div>
                <div className="dialogue-controls" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 10 }}>
                  {segment.options.map((opt, idx) => (
                    <button
                      key={idx}
                      className="btn btn-ghost"
                      style={{ textAlign: 'left', whiteSpace: 'normal', height: 'auto', padding: '12px 16px' }}
                      onClick={() => chooseScene(opt.target)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {mode === 'playing' && segment?.kind === 'interactive' && interaction && (
        <div className="main-content" style={{ gridTemplateColumns: '1fr' }}>
          <div className="panel" style={{ maxWidth: 900, margin: '0 auto', width: '100%' }}>
            <InteractionStage
              key={segmentIdx}
              interaction={interaction}
              onComplete={nextSegment}
              setPlayer={setPlayer}
            />
          </div>
        </div>
      )}

      {mode === 'playing' && segment?.kind === 'mission' && challenge && (
        <main className="main-content">
          <ChallengePanel
            key={segmentIdx}
            challenge={challenge}
            onSuccess={handleChallengeSuccess}
          />
        </main>
      )}

      {mode === 'dragon' && dragonData && (
        <DragonOverlay dragonData={dragonData} onDismiss={handleDragonDismiss} />
      )}

      {/* A mission sits mid-scene, so its reward returns to the beat stream
          rather than ending the chapter. */}
      {mode === 'reward' && rewardData && (
        <RewardPopup
          reward={rewardData.reward}
          statBonuses={rewardData.statBonuses}
          onDismiss={nextSegment}
        />
      )}
    </>
  );
}
