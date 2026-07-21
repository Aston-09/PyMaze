// Single source for the backend origin. Set VITE_API_BASE at build time to
// point a deployed frontend at a deployed backend; dev falls back to local.
const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const API_URL = `${BASE}/api`
export const ASSET_URL = `${BASE}/assets`
