/**
 * services/api.js
 * ---------------
 * Centralized API client for the Fake ID Screening backend.
 * All backend communication goes through this module.
 * Never import backend URL directly in components — use this service.
 */

// When VITE_API_BASE_URL is empty (the default with the Vite proxy), all URLs
// are relative (e.g. /health, /api/v1/screen) and Vite forwards them to the
// backend at http://127.0.0.1:8000 — bypassing CORS entirely.
// To call the backend directly (e.g. in production), set VITE_API_BASE_URL to
// the full backend URL in your deployment .env.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';


/**
 * Internal fetch wrapper. Throws a normalized error object on non-2xx responses.
 */
async function apiFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  let response;
  try {
    response = await fetch(url, options);
  } catch (networkErr) {
    throw { type: 'network', message: 'Cannot reach the server. Please check your connection.' };
  }

  if (!response.ok) {
    let detail = `Server returned ${response.status}.`;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail = typeof body.detail === 'string'
          ? body.detail
          : JSON.stringify(body.detail);
      }
    } catch (_) { /* ignore JSON parse failure */ }

    throw {
      type: 'api',
      status: response.status,
      message: detail,
    };
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

/** GET /health — returns { status: "ok" } */
export async function healthCheck() {
  return apiFetch('/health');
}

// ---------------------------------------------------------------------------
// Screening pipeline
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/screen
 * Uploads document_front, document_back, live_photo as multipart/form-data.
 * Returns a ScreeningResponse object.
 */
export async function submitScreening(documentFront, documentBack, livePhoto) {
  const form = new FormData();
  form.append('document_front', documentFront);
  form.append('document_back', documentBack);
  form.append('live_photo', livePhoto);

  return apiFetch('/api/v1/screen', {
    method: 'POST',
    body: form,
    // Do NOT set Content-Type — browser sets it automatically with the boundary.
  });
}

// ---------------------------------------------------------------------------
// Screening records
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/screenings?limit=&offset=
 * Returns { items: [], total: number, limit, offset }
 */
export async function getScreenings(limit = 50, offset = 0) {
  return apiFetch(`/api/v1/screenings?limit=${limit}&offset=${offset}`);
}

/**
 * GET /api/v1/screenings/{screening_id}
 * Returns a full ScreeningRecordSchema object.
 */
export async function getScreeningById(screeningId) {
  return apiFetch(`/api/v1/screenings/${encodeURIComponent(screeningId)}`);
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/stats/summary
 * Returns { total, verified, suspicious, rejected }
 */
export async function getStatsSummary() {
  return apiFetch('/api/v1/stats/summary');
}

/**
 * GET /api/v1/stats/trend
 * Returns { data: [{ date, count }] } for the last 7 days.
 */
export async function getStatsTrend() {
  return apiFetch('/api/v1/stats/trend');
}
