/**
 * Type definitions mirroring the backend screening contract.
 *
 * Source of truth: `backend/schemas/screening.py` on the project's
 * `feature/backend` branch (read-only reference).
 *
 * Endpoint: POST /api/v1/screen  (multipart/form-data)
 *   fields: document_front, document_back, live_photo
 */

/** Status values documented by the backend `ScreeningResponse` schema. */
export const SCREENING_STATUSES = [
  'completed',
  'student_not_found',
  'student_blacklisted',
  'student_inactive',
  'expired',
  'document_validation_failed',
  'reference_image_missing',
  'face_not_detected',
  'face_mismatch',
  'error',
] as const;

export type KnownScreeningStatus = (typeof SCREENING_STATUSES)[number];

/**
 * The backend may add statuses over time, so we accept any string while
 * keeping autocomplete for the known set.
 */
export type ScreeningStatus = KnownScreeningStatus | (string & {});

/** Subset of the student record returned by the backend. */
export interface StudentSummary {
  student_id: string;
  name: string;
  course: string | null;
  college: string | null;
  dob: string | null;
  valid_till: string | null;
  /** "active" | "expired" | "suspended" per backend docs. */
  status: string;
  blacklisted: boolean;
}

/** Face comparison outcome. `confidence` is a cosine similarity in 0.0–1.0. */
export interface FaceVerificationResult {
  match: boolean;
  confidence: number;
}

/** Response body of POST /api/v1/screen. */
export interface ScreeningResponse {
  screening_id: string;
  status: ScreeningStatus;
  student: StudentSummary | null;
  face_verification: FaceVerificationResult | null;
  message: string;
}

/** Generic FastAPI error body: `{ "detail": "..." }`. */
export interface ApiErrorBody {
  detail?: string;
}

/** The three images the pipeline requires, in capture order. */
export type CaptureSlot = 'documentFront' | 'documentBack' | 'livePhoto';

/** A locally captured (or picked) image awaiting upload. */
export interface CapturedImage {
  /** Local file URI on device. */
  uri: string;
  width: number;
  height: number;
  /** Multipart filename sent to the backend. */
  fileName: string;
  /** MIME type sent to the backend. */
  mimeType: 'image/jpeg' | 'image/png';
  /** Byte size after preparation, when known. */
  sizeBytes?: number;
  capturedAt: number;
}

export type CaptureBundle = Record<CaptureSlot, CapturedImage | null>;
