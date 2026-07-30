import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { API_URL } from '../config';
import './LoginScreen.css'; // We will create some basic CSS for this

const LoginScreen = () => {
  const { login } = useContext(AuthContext);
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (isRegistering) {
      try {
        const res = await fetch(`${API_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, email, password }),
        });
        if (res.ok) {
          setIsRegistering(false);
          setError('Registration successful! Please login.');
        } else {
          const data = await res.json();
          if (Array.isArray(data.detail)) {
            setError(data.detail.map(err => err.msg).join(', '));
          } else {
            setError(data.detail || 'Registration failed.');
          }
        }
      } catch (err) {
        setError('Server error.');
      }
    } else {
      try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        
        const res = await fetch(`${API_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData,
        });
        if (res.ok) {
          const data = await res.json();
          login(data.access_token);
        } else {
          const data = await res.json();
          if (Array.isArray(data.detail)) {
            setError(data.detail.map(err => err.msg).join(', '));
          } else {
            setError(data.detail || 'Login failed.');
          }
        }
      } catch (err) {
        setError('Server error.');
      }
    }
  };

  return (
    <div className="login-screen">
      <div className="login-box panel">
        <h1 className="login-title">PyMaze</h1>
        <p className="login-subtitle">
          {isRegistering ? 'Create your character.' : 'Enter the world.'}
        </p>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            className="login-input"
          />
          {isRegistering && (
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="login-input"
            />
          )}
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="login-input"
          />
          <button type="submit" className="login-button">
            {isRegistering ? 'Register' : 'Login'}
          </button>
        </form>

        <p className="login-toggle">
          {isRegistering ? 'Already have an account? ' : 'New to PyMaze? '}
          <button onClick={() => setIsRegistering(!isRegistering)} className="login-toggle-button">
            {isRegistering ? 'Login here.' : 'Register here.'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginScreen;
