import React, { useState, useEffect, useContext } from 'react';
import HUD from './components/HUD';
import SceneManager from './components/SceneManager';
import LoginScreen from './components/LoginScreen';
import PlayerProfile from './components/PlayerProfile';
import Sidebar from './components/Sidebar';
import AppearancePicker from './components/AppearancePicker';
import { AuthContext } from './context/AuthContext';

import { apiFetch } from './utils/api';


function App() {
  const { isAuthenticated, token, logout } = useContext(AuthContext);
  const [player, setPlayer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // Fetch initial player state
  useEffect(() => {
    const fetchPlayer = async () => {
      if (!isAuthenticated || !token) {
        setPlayer(null);
        return;
      }
      
      setLoading(true);
      try {
        const res = await apiFetch('/player');

        if (res.ok) {
          const data = await res.json();
          setPlayer(data);
          setError(null);
        } else if (res.status === 401) {
          logout();
        } else {
          setError(`Server Error (${res.status}): The backend couldn't be reached or had an internal error.`);
        }
      } catch (err) {
        console.error('Failed to fetch player:', err);
        setError('Network Error: Could not connect to the backend server. Please make sure the server and database are running.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchPlayer();
  }, [isAuthenticated, token, logout]);

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  if (loading) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="loading-spinner" style={{ width: 40, height: 40 }} />
      </div>
    );
  }

  // A backend that never answered used to leave a blank page and a message
  // only the console saw.
  if (error || !player) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="panel" style={{ maxWidth: 480, textAlign: 'center' }}>
          <h2>Can't reach the world</h2>
          <p>{error || 'No player data came back from the server.'}</p>
          <button className="btn" onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  // One-time gate: every later scene can write `background: player` because
  // the choice was made here.
  if (!player.gender) {
    return <AppearancePicker onChosen={setPlayer} />;
  }

  return (
    <div className="app-container">
      <HUD 
        player={player} 
        isSidebarOpen={isSidebarOpen} 
        toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} 
        onOpenProfile={() => setIsProfileOpen(true)}
      />
      
      {isProfileOpen && <PlayerProfile player={player} onClose={() => setIsProfileOpen(false)} />}
      
      <div style={{ display: 'flex', flex: 1, gap: '1.5rem', minHeight: 0 }}>
        {isSidebarOpen && <Sidebar player={player} />}
        <SceneManager player={player} setPlayer={setPlayer} />
      </div>
    </div>
  );
}

export default App;
