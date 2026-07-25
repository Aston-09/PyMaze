import React, { useState, useEffect, useContext } from 'react';
import HUD from './components/HUD';
import SceneManager from './components/SceneManager';
import Sidebar from './components/Sidebar';
import PlayerProfile from './components/PlayerProfile';
import LoginScreen from './components/LoginScreen';
import { AuthContext } from './context/AuthContext';

import { API_URL } from './config';

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
        const res = await fetch(`${API_URL}/player`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
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

  if (error) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="panel" style={{ maxWidth: 600, textAlign: 'center', borderColor: 'var(--seal-red)' }}>
          <h2 style={{ color: 'var(--seal-red)' }}>Connection Lost</h2>
          <p>{error}</p>
          <button className="btn" onClick={() => window.location.reload()} style={{ marginTop: '1rem' }}>
            Try Again
          </button>
        </div>
      </div>
    );
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
