/**
 * Minimal fetch wrapper: URL construction, timeout, abort and error
 * normalisation. No third-party HTTP library — `fetch`, `FormData` and
 * `AbortController` all ship with React Native.
 */

import { API_TIMEOUT_MS, buildApiUrl, isApiConfigured } from '../config/env';
import {
  ApiError,
  cancelledError,
  configError,
  malformedResponseError,
  httpError,
  networkError,
  timeoutError,
  toApiError,
} from './errors';

export interface RequestOptions {
  /** Caller-owned signal, e.g. cancelled when the screen unmounts. */
  signal?: AbortSignal;
  /** Overrides {@link API_TIMEOUT_MS} for a single call. */
  timeoutMs?: number;
}

/**
 * POSTs `FormData` and parses a JSON response.
 *
 * The `Content-Type` header is intentionally **not** set: React Native's
 * `fetch` generates the `multipart/form-data` boundary from the `FormData`
 * body itself, and setting it manually corrupts the request.
 */
export async function postFormData<T>(
  path: string,
  body: FormData,
  options: RequestOptions = {},
): Promise<T> {
  if (!isApiConfigured()) {
    throw configError('EXPO_PUBLIC_API_BASE_URL missing or not an http(s) URL.');
  }

  const url = buildApiUrl(path);
  const timeoutMs = options.timeoutMs ?? API_TIMEOUT_MS;

  // Two abort sources: our timeout and the caller's signal.
  const controller = new AbortController();
  let timedOut = false;

  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  const abortFromCaller = () => controller.abort();
  const callerSignal = options.signal;

  if (callerSignal) {
    if (callerSignal.aborted) {
      clearTimeout(timer);
      throw cancelledError();
    }
    callerSignal.addEventListener('abort', abortFromCaller);
  }

  let response: Response;

  try {
    response = await fetch(url, {
      method: 'POST',
      body,
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
  } catch (cause) {
    if (timedOut) throw timeoutError(timeoutMs);
    if (isAbort(cause)) throw cancelledError();
    throw networkError(cause instanceof Error ? `${cause.name}: ${cause.message}` : String(cause));
  } finally {
    clearTimeout(timer);
    callerSignal?.removeEventListener('abort', abortFromCaller);
  }

  const rawBody = await readBodyText(response);

  if (!response.ok) {
    throw httpError(response.status, extractServerDetail(rawBody));
  }

  const parsed = parseJson(rawBody);
  if (parsed === undefined) {
    throw malformedResponseError('Response body was not valid JSON.');
  }

  return parsed as T;
}

function isAbort(cause: unknown): boolean {
  return (
    typeof cause === 'object' &&
    cause !== null &&
    'name' in cause &&
    (cause as { name?: unknown }).name === 'AbortError'
  );
}

/** Body reading can itself fail mid-stream; treat that as a network fault. */
async function readBodyText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch (cause) {
    if (!response.ok) {
      // Status is still meaningful even without a body.
      throw httpError(response.status);
    }
    throw toApiError(cause);
  }
}

/** `undefined` signals "not JSON" (as opposed to a valid `null` body). */
function parseJson(raw: string): unknown {
  if (raw.trim().length === 0) return undefined;
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return undefined;
  }
}

/** Pulls FastAPI's `{"detail": ...}` out of an error body, when present. */
function extractServerDetail(raw: string): string | undefined {
  const parsed = parseJson(raw);

  if (typeof parsed === 'object' && parsed !== null) {
    // `detail` is a string for HTTPException, but a list of validation
    // objects for 422 responses, so it is read as `unknown` first.
    const detail: unknown = (parsed as Record<string, unknown>).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: unknown } | undefined;
      if (first && typeof first.msg === 'string') return first.msg;
    }
    return undefined;
  }

  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

export { ApiError };
