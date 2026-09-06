/**
 * services/screeningHelpers.js
 * ----------------------------
 * Utility functions that convert raw backend ScreeningRecordSchema
 * fields into the display values the existing UI components expect.
 */

/**
 * Maps a backend `status` string to one of the four Badge decision strings.
 *   completed                 → "Verified"
 *   document_tampered         → "Document Tampered"
 *   suspicious                → "Suspicious"
 *   rejected                  → "Rejected"
 *   face_mismatch             → "Rejected"
 *   face_not_detected         → "Suspicious"
 *   student_not_found         → "Rejected"
 *   student_blacklisted       → "Rejected"
 *   student_inactive          → "Suspicious"
 *   reference_image_missing   → "Suspicious"
 *   document_validation_failed→ "Suspicious"
 *   expired                   → "Suspicious"
 *   (anything else)           → "Rejected"
 */
export function statusToDecision(status) {
  switch (status) {
    case 'completed':
      return 'Verified';
    case 'document_tampered':
      return 'Document Tampered';
    case 'suspicious':
      return 'Suspicious';
    case 'rejected':
    case 'face_mismatch':
    case 'student_not_found':
    case 'student_blacklisted':
      return 'Rejected';
    case 'face_not_detected':
    case 'student_inactive':
    case 'reference_image_missing':
    case 'document_validation_failed':
    case 'expired':
      return 'Suspicious';
    default:
      return 'Rejected';
  }
}

/**
 * Returns a human-readable description of the screening outcome
 * when the backend `validation_issues.message` is absent or generic.
 */
export function statusToReason(status, message) {
  if (message && message !== status) return message;
  switch (status) {
    case 'completed':
      return 'All verification checks passed. Identity confirmed.';
    case 'document_tampered':
      return 'Document tampering was detected on one or more sides. The document may have been altered.';
    case 'suspicious':
      return 'Screening flagged this document as suspicious. Manual review is required.';
    case 'rejected':
      return 'Screening was rejected. The document or identity could not be verified.';
    case 'face_mismatch':
      return 'Face verification failed. The person does not match the database reference photo.';
    case 'face_not_detected':
      return 'No face was detected in the submitted live photo. Please re-submit with a clear face photo.';
    case 'student_not_found':
      return 'No student record found for the extracted ID. The document may be forged or from an unregistered institution.';
    case 'student_blacklisted':
      return 'Student is flagged as blacklisted. Access denied per security policy.';
    case 'student_inactive':
      return 'Student account is not active. The card may be expired or suspended.';
    case 'reference_image_missing':
      return 'No reference image is available in the database for this student. Face verification could not be performed.';
    case 'document_validation_failed':
      return 'Document field validation failed. One or more fields on the document do not match database records.';
    case 'expired':
      return 'Student account has expired. Access denied.';
    default:
      return 'Screening could not be completed. Please contact an administrator.';
  }
}

/**
 * Safely parse a timestamp string as UTC.
 *
 * The backend stores naive UTC datetimes (no +00:00 / Z suffix) for historical
 * records. JavaScript's Date() treats strings WITHOUT a timezone suffix as
 * **local time**, causing a 5:30-hour display error in IST.
 *
 * Fix: if the string has no timezone indicator, append 'Z' before parsing so
 * JS always interprets it as UTC.  New records serialised by Pydantic with
 * datetime(timezone.utc) will already carry '+00:00' and are unaffected.
 */
function parseUTC(ts) {
  if (!ts) return null;
  // Already has timezone info: +HH:MM, -HH:MM, or trailing Z
  if (/([Zz]|[+-]\d{2}:\d{2})$/.test(ts)) return new Date(ts);
  // Naive string — treat as UTC
  return new Date(ts + 'Z');
}

/**
 * Formats a timestamp for full display in IST (Asia/Kolkata).
 */
export function formatTimestamp(ts) {
  if (!ts) return '—';
  try {
    const d = parseUTC(ts);
    if (!d || isNaN(d)) return ts;
    return new Intl.DateTimeFormat('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'Asia/Kolkata',
    }).format(d);
  } catch (_) {
    return ts;
  }
}

/**
 * Formats a timestamp as time-only in IST (Asia/Kolkata).
 */
export function formatTime(ts) {
  if (!ts) return '—';
  try {
    const d = parseUTC(ts);
    if (!d || isNaN(d)) return ts;
    return new Intl.DateTimeFormat('en-IN', {
      timeStyle: 'short',
      timeZone: 'Asia/Kolkata',
    }).format(d);
  } catch (_) {
    return ts;
  }
}

/**
 * Returns a color token string based on risk_score value (0–100).
 */
export function riskColor(score) {
  if (score == null) return 'var(--text-muted)';
  if (score > 60) return 'var(--danger)';
  if (score > 30) return 'var(--warning)';
  return 'var(--success)';
}

/**
 * Returns a color token string based on backend risk_level string.
 * Low → success, Medium → warning, High / Critical → danger.
 */
export function riskLevelColor(level) {
  switch ((level || '').toLowerCase()) {
    case 'low':      return 'var(--success)';
    case 'medium':   return 'var(--warning)';
    case 'high':
    case 'critical': return 'var(--danger)';
    default:         return 'var(--text-muted)';
  }
}
