/**
 * services/screeningHelpers.js
 * ----------------------------
 * Utility functions that convert raw backend ScreeningRecordSchema
 * fields into the display values the existing UI components expect.
 */

/**
 * Maps a backend `status` string to one of the three Badge decision strings.
 *   completed              → "Verified"
 *   face_mismatch          → "Rejected"
 *   face_not_detected      → "Suspicious"
 *   student_not_found      → "Rejected"
 *   student_blacklisted    → "Rejected"
 *   student_inactive       → "Suspicious"
 *   reference_image_missing→ "Suspicious"
 *   (anything else)        → "Rejected"
 */
export function statusToDecision(status) {
  switch (status) {
    case 'completed':
      return 'Verified';
    case 'face_mismatch':
    case 'student_not_found':
    case 'student_blacklisted':
      return 'Rejected';
    case 'face_not_detected':
    case 'student_inactive':
    case 'reference_image_missing':
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
    default:
      return 'Screening could not be completed. Please contact an administrator.';
  }
}

/**
 * Formats an ISO timestamp string for display.
 */
export function formatTimestamp(ts) {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch (_) {
    return ts;
  }
}

/**
 * Formats an ISO timestamp string for short display (time only).
 */
export function formatTime(ts) {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return ts;
  }
}

/**
 * Returns a color token string based on risk_score value.
 */
export function riskColor(score) {
  if (score == null) return 'var(--text-muted)';
  if (score > 60) return 'var(--danger)';
  if (score > 30) return 'var(--warning)';
  return 'var(--success)';
}
