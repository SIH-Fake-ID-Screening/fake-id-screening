import type { SemanticTone } from '../theme';
import type { CaptureSlot, ScreeningResponse, ScreeningStatus } from '../types/screening';

/**
 * The single recovery action offered for an outcome.
 *
 * `resubmit` sends the same three photos again (useful when the failure was
 * server-side), `recapture` reopens the camera for the one photo that is
 * actually implicated, and `restart` begins a whole new verification.
 */
export type RetryAction =
  | { mode: 'resubmit'; label: string }
  | { mode: 'recapture'; slot: CaptureSlot; label: string }
  | { mode: 'restart'; label: string };

/** How a screening outcome should be presented to the user. */
export interface StatusPresentation {
  /** Overall verdict driving the visual treatment. */
  outcome: 'verified' | 'rejected' | 'inconclusive';
  tone: SemanticTone;
  icon: string;
  /** Short headline, e.g. "Identity verified". */
  title: string;
  /** Plain-language explanation of what happened. */
  summary: string;
  /** What the user can do next. */
  advice: string;
  /** True when the student panel is worth showing. */
  showStudentDetails: boolean;
  /** True when the face-verification panel is worth showing. */
  showFaceDetails: boolean;
  /**
   * The recovery action to offer, or `null` when retrying genuinely cannot
   * help (blacklisted, inactive, expired, missing reference photo).
   */
  retry: RetryAction | null;
}

const RETAKE_SELFIE: RetryAction = {
  mode: 'recapture',
  slot: 'livePhoto',
  label: 'Retake selfie',
};

const RETAKE_ID_FRONT: RetryAction = {
  mode: 'recapture',
  slot: 'documentFront',
  label: 'Retake ID photos',
};

const RESUBMIT: RetryAction = { mode: 'resubmit', label: 'Try again' };

const PRESENTATIONS: Record<string, StatusPresentation> = {
  student_not_found: {
    outcome: 'rejected',
    tone: 'danger',
    icon: '⚠',
    title: 'No matching record',
    summary:
      'The student ID read from the document does not match any record in the institutional database.',
    advice:
      'Check that the correct ID card was photographed and that the ID number is fully visible, then try again.',
    showStudentDetails: false,
    showFaceDetails: false,
    retry: RETAKE_ID_FRONT,
  },
  student_blacklisted: {
    outcome: 'rejected',
    tone: 'danger',
    icon: '⛔',
    title: 'Access denied',
    summary:
      'This student record is blacklisted, so verification was stopped before any face check ran.',
    advice: 'Contact the issuing institution — this cannot be resolved by retrying.',
    showStudentDetails: true,
    showFaceDetails: false,
    retry: null,
  },
  student_inactive: {
    outcome: 'rejected',
    tone: 'danger',
    icon: '⛔',
    title: 'Account not active',
    summary:
      'The student record exists but is not currently active, so verification was stopped early.',
    advice: 'Contact the issuing institution to have the record reactivated.',
    showStudentDetails: true,
    showFaceDetails: false,
    retry: null,
  },
  expired: {
    outcome: 'rejected',
    tone: 'danger',
    icon: '🗓',
    title: 'ID has expired',
    summary: 'The validity date on this student record has already passed.',
    advice: 'A renewed ID card is required before this identity can be verified.',
    showStudentDetails: true,
    showFaceDetails: false,
    retry: null,
  },
  document_validation_failed: {
    outcome: 'inconclusive',
    tone: 'warning',
    icon: '📄',
    title: 'Document could not be validated',
    summary:
      'The details read from the document did not line up with the institutional record — most often the validity date could not be read or did not match.',
    advice:
      'Retake both sides of the card in good light, keeping the validity date sharp and fully in frame.',
    showStudentDetails: true,
    showFaceDetails: false,
    retry: RETAKE_ID_FRONT,
  },
  reference_image_missing: {
    outcome: 'inconclusive',
    tone: 'warning',
    icon: '🖼',
    title: 'Face check unavailable',
    summary:
      'The record was found, but the institution has no reference photo on file, so the face comparison could not run.',
    advice: 'This needs to be fixed on the institution side — retrying will not help.',
    showStudentDetails: true,
    showFaceDetails: false,
    retry: null,
  },
  face_not_detected: {
    outcome: 'inconclusive',
    tone: 'warning',
    icon: '🙈',
    title: 'No clear face found',
    summary: 'A usable face could not be detected in one of the photos used for comparison.',
    advice:
      'Retake the selfie face-on in even light, with nothing covering your face, and only one person in frame.',
    showStudentDetails: true,
    showFaceDetails: false,
    retry: RETAKE_SELFIE,
  },
  face_mismatch: {
    outcome: 'rejected',
    tone: 'danger',
    icon: '✖',
    title: 'Face did not match',
    summary: 'The live selfie did not match the reference photo held for this student record.',
    advice:
      'If this is your own ID, retake the selfie face-on in better light. Repeated mismatches are referred for manual review.',
    showStudentDetails: true,
    showFaceDetails: true,
    retry: RETAKE_SELFIE,
  },
  error: {
    outcome: 'inconclusive',
    tone: 'warning',
    icon: '⚙',
    title: 'Screening could not complete',
    summary: 'The screening service hit an unexpected problem while processing the submission.',
    advice:
      'Please submit the same photos again in a moment. If it keeps failing, report it to the operator.',
    showStudentDetails: false,
    showFaceDetails: false,
    retry: RESUBMIT,
  },
};

const COMPLETED_MATCH: StatusPresentation = {
  outcome: 'verified',
  tone: 'success',
  icon: '✓',
  title: 'Identity verified',
  summary:
    'The document details matched an active institutional record and the live selfie matched the official reference photo.',
  advice: 'No further action needed.',
  showStudentDetails: true,
  showFaceDetails: true,
  retry: null,
};

const COMPLETED_NO_FACE_RESULT: StatusPresentation = {
  outcome: 'inconclusive',
  tone: 'warning',
  icon: '?',
  title: 'Partially verified',
  summary:
    'The document details matched an institutional record, but no face-comparison result was returned.',
  advice: 'Submit the same photos again so the face check can complete.',
  showStudentDetails: true,
  showFaceDetails: false,
  retry: RESUBMIT,
};

const UNKNOWN_STATUS: StatusPresentation = {
  outcome: 'inconclusive',
  tone: 'neutral',
  icon: '?',
  title: 'Result needs review',
  summary:
    'The screening service returned an outcome this app version does not recognise, so it cannot be interpreted with confidence.',
  advice: 'Treat this as unverified and refer it for manual review.',
  showStudentDetails: true,
  showFaceDetails: true,
  retry: { mode: 'restart', label: 'Start a new verification' },
};

/** Shown when the screen somehow has no usable response object at all. */
export const MISSING_RESULT: StatusPresentation = {
  outcome: 'inconclusive',
  tone: 'neutral',
  icon: '?',
  title: 'No result available',
  summary: 'The screening result could not be read, so nothing can be reported for this attempt.',
  advice: 'Please run the verification again.',
  showStudentDetails: false,
  showFaceDetails: false,
  retry: { mode: 'restart', label: 'Start a new verification' },
};

/**
 * Maps a backend screening result onto user-facing copy and visual treatment.
 *
 * Raw status strings are never shown as the primary message, and an unknown or
 * malformed status falls back to a safe "needs review" state rather than being
 * treated as a pass. Nothing here infers a verdict the backend did not send.
 */
export function presentScreeningResult(
  result: ScreeningResponse | null | undefined,
): StatusPresentation {
  if (!result || typeof result !== 'object') return MISSING_RESULT;

  const rawStatus: ScreeningStatus = typeof result.status === 'string' ? result.status : '';
  // Tolerate casing/whitespace differences without inventing new meanings.
  const status = rawStatus.trim().toLowerCase();

  if (status.length === 0) return MISSING_RESULT;

  if (status === 'completed') {
    const face = result.face_verification;
    if (!face) return COMPLETED_NO_FACE_RESULT;
    return face.match ? COMPLETED_MATCH : PRESENTATIONS.face_mismatch;
  }

  return PRESENTATIONS[status] ?? UNKNOWN_STATUS;
}

/**
 * Describes the face-match similarity score in words.
 *
 * The backend documents `confidence` as a cosine similarity between face
 * embeddings (0.0–1.0), which is NOT a probability — so it is deliberately not
 * labelled as a percentage likelihood. We show the raw score plus a band.
 */
export function describeSimilarity(confidence: number): {
  score: string;
  band: string;
  tone: SemanticTone;
} {
  if (typeof confidence !== 'number' || !Number.isFinite(confidence)) {
    return { score: '—', band: 'Not available', tone: 'neutral' };
  }

  const clamped = Math.min(Math.max(confidence, 0), 1);
  const score = clamped.toFixed(2);

  if (clamped >= 0.75) return { score, band: 'Strong similarity', tone: 'success' };
  if (clamped >= 0.5) return { score, band: 'Moderate similarity', tone: 'warning' };
  return { score, band: 'Low similarity', tone: 'danger' };
}
