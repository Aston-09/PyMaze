import React, { useState, useEffect, useCallback, useMemo } from 'react';
import DialogueBox from './DialogueBox';
import ChallengePanel from './ChallengePanel';
import RewardPopup from './RewardPopup';
import DragonOverlay from './DragonOverlay';
import EndScreen from './EndScreen';
import InteractionStage from './interactions/InteractionStage';
import SceneBackground from './SceneBackground';
import SystemPanel from './SystemPanel';

import { apiFetch } from '../utils/api';

/**
 * Collapse a scene's beat stream into playable segments.
 *
 * Consecutive dialogue beats become one segment so prose still flows under a
 * single "Next", while interactions and missions each stand alone. This is
 * what lets a chapter teach → play → teach → test inside one scene.
 */
function toSegments(beats = []) {
  const segments = [];
  // `background:` is scenery, not a step the player clicks through — it sets
  // the location for every segment that follows until the next one.
  let background = null;

  for (const beat of beats) {
    const last = segments[segments.length - 1];

    if (beat.type === 'background') {
      background = beat.ref;
    } else if (beat.type === 'dialogue') {
      // Merge into the running dialogue block, unless the location just
      // changed — a new place deserves its own reveal.
      if (last?.kind === 'dialogue' && last.background === background) {
        last.dialogues.push({ speaker: beat.speaker, lines: beat.lines });
      } else {
        segments.push({
          kind: 'dialogue',
          background,
          dialogues: [{ speaker: beat.speaker, lines: beat.lines }],
        });
      }
    } else if (beat.type === 'system') {
      // Always its own segment — a System panel interrupts, by design.
      segments.push({ kind: 'system', background, ref: beat.ref, lines: beat.lines });
    } else if (beat.type === 'interactive') {
      segments.push({ kind: 'interactive', background, ref: beat.ref });
    } else if (beat.type === 'mission') {
      segments.push({ kind: 'mission', background, ref: beat.ref });
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

  const segments = useMemo(() => toSegments(scene?.beats), [scene]);
  const segment = segments[segmentIdx];

  const fetchScene = useCallback(async (sceneId) => {
    try {
      setMode('loading');
      const res = await apiFetch(`/scene/${sceneId}`);
      if (!res.ok) {
        setMode('end');
        return;
      }
      const data = await res.json();
      setScene(data);
      setSegmentIdx(0);
      setMode(data.beats?.length ? 'playing' : 'end');
    } catch (err) {
      console.error('Failed to fetch scene:', err);
      setMode('end');
    }
  }, []);

  useEffect(() => {
    if (player?.current_scene) {
      fetchScene(player.current_scene);
    } else {
      setMode('end');
    }
    // Only on mount — later scene changes go through advanceToScene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const advanceToScene = useCallback(async (currentSceneId) => {
    try {
      setMode('loading');
      const res = await apiFetch(`/advance`, {
        method: 'POST',
        body: JSON.stringify({ current_scene: currentSceneId }),
      });
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
      setMode('end');
    }
  }, [fetchScene, setPlayer]);

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

  if (mode === 'end') return <EndScreen player={player} />;

  const challenge = segment?.kind === 'mission' ? scene?.challenges?.[segment.ref] : null;
  const interaction = segment?.kind === 'interactive' ? scene?.interactions?.[segment.ref] : null;

  // The world is shown behind narration only. Coding and puzzle beats keep a
  // clean page so nothing competes with the work. System panels keep it too —
  // they read as an overlay on the world, so the world stays visible.
  const showBackground = segment?.kind === 'dialogue' || segment?.kind === 'system';

  return (
    <>
      {showBackground && <SceneBackground src={segment.background} />}

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
