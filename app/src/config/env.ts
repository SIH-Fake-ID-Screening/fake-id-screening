/**
 * Runtime configuration read from Expo public environment variables.
 *
 * `EXPO_PUBLIC_*` variables are inlined by the Expo/Metro Babel transform at
 * bundle time, so they are read directly off `process.env` and must be
 * referenced statically (no dynamic key lookup).
 *
 * The backend is not deployed yet, so there is deliberately **no** default
 * URL: an unconfigured app must fail loudly instead of calling something
 * arbitrary. See `app/README.md` for local-development setup.
 */

/** Trailing slashes are stripped so path joining can never double up. */
function normaliseBaseUrl(raw: string | undefined): string | null {
  if (typeof raw !== 'string') return null;

  const trimmed = raw.trim().replace(/\/+$/, '');
  if (trimmed.length === 0) return null;

  // Guard against `localhost:8000` style values missing a scheme, which
  // `fetch` would treat as a relative URL.
  if (!/^https?:\/\//i.test(trimmed)) return null;

  return trimmed;
}

/**
 * The configured API origin (e.g. `http://192.168.1.20:8000`), or `null` when
 * the app has no server address configured.
 */
export const API_BASE_URL: string | null = normaliseBaseUrl(
  process.env.EXPO_PUBLIC_API_BASE_URL,
);

/** Raw value, used only to explain misconfiguration during development. */
export const RAW_API_BASE_URL: string | undefined = process.env.EXPO_PUBLIC_API_BASE_URL;

export function isApiConfigured(): boolean {
  return API_BASE_URL !== null;
}

/** Version prefix used by the backend router. */
export const API_VERSION_PREFIX = '/api/v1';

const DEFAULT_TIMEOUT_MS = 90_000;

function parseTimeout(raw: string | undefined): number {
  const parsed = Number.parseInt(String(raw ?? ''), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_TIMEOUT_MS;
  // Keep it sane: 5s–5min.
  return Math.min(Math.max(parsed, 5_000), 300_000);
}

/**
 * Upload + screening timeout. The pipeline runs OCR and face verification
 * server-side, so this is generous by design.
 */
export const API_TIMEOUT_MS: number = parseTimeout(process.env.EXPO_PUBLIC_API_TIMEOUT_MS);

/**
 * Joins the configured origin, the version prefix and an endpoint path
 * without ever producing `//` or dropping a segment.
 *
 * @throws when no base URL is configured — callers should check
 *         {@link isApiConfigured} first, or catch and surface a config error.
 */
export function buildApiUrl(path: string): string {
  if (API_BASE_URL === null) {
    throw new Error('EXPO_PUBLIC_API_BASE_URL is not configured.');
  }

  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${API_VERSION_PREFIX}${suffix}`;
}
