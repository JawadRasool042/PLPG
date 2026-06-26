/**
 * Single source of truth for the Flask API root (no trailing slash).
 *
 * Development: defaults to `/api` so requests stay same-origin; Vite proxies
 * to Flask (see vite.config.ts). This avoids CORS and many "Failed to fetch"
 * cases when the UI is opened as http://localhost:5173 but CORS/origin rules
 * differ from http://localhost:5000.
 *
 * Override anytime with VITE_API_BASE_URL (required for production builds).
 */
const raw = import.meta.env.VITE_API_BASE_URL?.trim();
const normalized = raw ? raw.replace(/\/$/, '') : null;

export const API_BASE_URL: string = (() => {
  if (normalized) return normalized;
  if (import.meta.env.PROD) {
    throw new Error(
      'VITE_API_BASE_URL is required in production. Set it before building (e.g. https://api.example.com/api).'
    );
  }
  return '/api';
})();

/** Map browser network failures to a clearer message for users. */
export function asFetchNetworkError(err: unknown): Error {
  if (err instanceof Error) {
    const m = err.message;
    if (
      err.name === 'TypeError' ||
      m === 'Failed to fetch' ||
      m === 'Load failed' ||
      m === 'NetworkError when attempting to fetch resource.'
    ) {
      return new Error(
        'Cannot reach the API. Start the Flask backend on port 5000, or set VITE_API_BASE_URL in .env. ' +
          'With npm run dev, the app uses /api and Vite proxies to the backend (see vite.config.ts).'
      );
    }
    return err;
  }
  return new Error(String(err));
}
