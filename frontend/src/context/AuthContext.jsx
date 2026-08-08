import React, { createContext, useState, useCallback, useMemo } from 'react';

export const AuthContext = createContext();

// `isAuthenticated` is derived from the token rather than stored beside it —
// two pieces of state for one fact is how they end up disagreeing.
export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('token'));

  // Stable identities: consumers put `login`/`logout` in effect dependency
  // arrays, and a fresh function every render re-runs those effects forever.
  const login = useCallback((newToken) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
  }, []);

  const value = useMemo(
    () => ({ token, isAuthenticated: !!token, login, logout }),
    [token, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
