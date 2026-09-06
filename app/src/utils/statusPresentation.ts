import type { SemanticTone } from '../theme';
import type { ScreeningResponse, ScreeningStatus } from '../types/screening';

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
  /** True when retrying the capture flow could plausibly help. */
  allowRetry: boolean;
}

const PRESENTATIONS: Record<string, Omit<StatusPresentation, 'outcome'> & { outcome: StatusPresentation['outcome'] }> = {
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
    allowRetry: true,
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
    allowRetry: false,
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
    allowRetry: false,
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
    allowRetry: false,
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
    allowRetry: true,
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
    allowRetry: false,
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
    allowRetry: true,
  },
  face_mismatch: {
    outcome: 'rejected',
    tone: 'danger',
    icon: '✖',
    title: 'Face did not match',
    summary:
      'The live selfie did not match the reference photo held for this student record.',
    advice:
      'If this is your own ID, retake the selfie face-on in better light. Repeated mismatches are referred for manual review.',
    showStudentDetails: true,
    showFaceDetails: true,
    allowRetry: true,
  },
  error: {
    outcome: 'inconclusive',
    tone: 'warning',
    icon: '⚙',
    title: 'Screening could not complete',
    summary: 'The screening service hit an unexpected problem while processing the submission.',
    advice: 'Please try again in a moment. If it keeps failing, report it to the operator.',
    showStudentDetails: false,
    showFaceDetails: false,
    allowRetry: true,
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
  allowRetry: false,
};

const COMPLETED_NO_FACE_RESULT: StatusPresentation = {
  outcome: 'inconclusive',
  tone: 'warning',
  icon: '?',
  title: 'Partially verified',
  summary:
    'The document details matched an institutional record, but no face-comparison result was returned.',
  advice: 'Run the verification again so the face check can complete.',
  showStudentDetails: true,
  showFaceDetails: false,
  allowRetry: true,
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
  allowRetry: true,
};

/**
 * Maps a backend screening result onto user-facing copy and visual treatment.
 *
 * Raw status strings are never shown as the primary message. Unknown statuses
 * fall back to a safe "needs review" state rather than being treated as a pass.
 */
export function presentScreeningResult(result: ScreeningResponse): StatusPresentation {
  const status: ScreeningStatus = result?.status ?? '';

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
  if (!Number.isFinite(confidence)) {
    return { score: '—', band: 'Not available', tone: 'neutral' };
  }

  const clamped = Math.min(Math.max(confidence, 0), 1);
  const score = clamped.toFixed(2);

  if (clamped >= 0.75) return { score, band: 'Strong similarity', tone: 'success' };
  if (clamped >= 0.5) return { score, band: 'Moderate similarity', tone: 'warning' };
  return { score, band: 'Low similarity', tone: 'danger' };
}
