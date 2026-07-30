import React, { useState, useEffect } from 'react';
import HUD from './components/HUD';
import SceneManager from './components/SceneManager';
import AppearancePicker from './components/AppearancePicker';

import { API_URL } from './config';

/**
 * App — Main shell for the application.
 *
 * Handles fetching the initial player state and rendering the HUD.
 * The actual scene logic, modes, and overlays are delegated to SceneManager.
 */
function App() {
  const [player, setPlayer] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch initial player state
  useEffect(() => {
    const fetchPlayer = async () => {
      try {
        const res = await fetch(`${API_URL}/player`);
        if (res.ok) {
          const data = await res.json();
          setPlayer(data);
        }
      } catch (err) {
        console.error('Failed to fetch player:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlayer();
  }, []);

  if (loading) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="loading-spinner" style={{ width: 40, height: 40 }} />
      </div>
    );
  }

  // A brand-new player picks their look once, before anything else loads —
  // every later scene that reflects the player back at them depends on it.
  if (player && !player.gender) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <AppearancePicker onChosen={setPlayer} />
      </div>
    );
  }

  return (
    <div className="app-container">
      <HUD player={player} />
      {/* 
        We pass player and setPlayer to SceneManager so it can update the player
        state globally (e.g. after earning rewards) which updates the HUD. 
      */}
      <SceneManager player={player} setPlayer={setPlayer} />
    </div>
  );
}

export default App;
