/**
 * POST /api/v1/screen — the app's only backend call.
 *
 * Sends the three locally captured images as `multipart/form-data` and returns
 * the backend's screening result verbatim. No screening logic, scoring or
 * result synthesis happens here: an unreachable or failing backend produces an
 * {@link ApiError}, never a fabricated result.
 */

import { postFormData, type RequestOptions } from './client';
import { invalidInputError, malformedResponseError } from './errors';
import { CAPTURE_ORDER, CAPTURE_SLOT_MAP } from '../constants/captureSlots';
import type {
  CaptureBundle,
  CapturedImage,
  FaceVerificationResult,
  ScreeningResponse,
  StudentSummary,
} from '../types/screening';

export const SCREEN_ENDPOINT = '/screen';

/** Backend limit: 10 MB per uploaded image. */
export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;

/**
 * React Native's `FormData` accepts this object shape for a file part and
 * turns it into a real multipart file entry. It is not part of the DOM
 * `FormData` typings, hence the cast at the call site.
 */
interface ReactNativeFilePart {
  uri: string;
  name: string;
  type: string;
}

/** Only formats the backend accepts; anything else is sent as JPEG. */
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png'] as const;

/**
 * Strips path separators and control characters from a filename so the
 * multipart header cannot be broken (or a path smuggled) by a value that came
 * back from the camera.
 */
function sanitiseFileName(raw: string): string {
  return raw
    .replace(/[\r\n"\\/]+/g, '')
    .replace(/\s+/g, '-')
    .trim();
}

function toFilePart(image: CapturedImage, fallbackName: string): ReactNativeFilePart {
  // Preserve what the camera actually produced; only fall back when the value
  // is absent or not a format the backend accepts.
  const type = ALLOWED_MIME_TYPES.includes(image.mimeType as (typeof ALLOWED_MIME_TYPES)[number])
    ? image.mimeType
    : 'image/jpeg';

  const extension = type === 'image/png' ? 'png' : 'jpg';

  const candidate =
    typeof image.fileName === 'string' ? sanitiseFileName(image.fileName) : '';

  // The extension must agree with the declared MIME type, otherwise servers
  // that sniff by name can reject an otherwise valid upload.
  const name =
    candidate.length > 0 && new RegExp(`\\.${extension}$`, 'i').test(candidate)
      ? candidate
      : `${fallbackName}.${extension}`;

  return { uri: image.uri.trim(), name, type };
}

/**
 * Builds the multipart body using the exact field names the backend expects:
 * `document_front`, `document_back`, `live_photo`.
 */
export function buildScreeningFormData(captures: CaptureBundle): FormData {
  const form = new FormData();

  for (const slot of CAPTURE_ORDER) {
    const meta = CAPTURE_SLOT_MAP[slot];
    const image = captures[slot];

    if (!image || typeof image.uri !== 'string' || image.uri.trim().length === 0) {
      throw invalidInputError(
        `The ${meta.label.toLowerCase()} photo is missing. Please capture all three photos before submitting.`,
        `Missing capture for slot "${slot}".`,
      );
    }

    if (typeof image.sizeBytes === 'number' && image.sizeBytes > MAX_IMAGE_BYTES) {
      throw invalidInputError(
        `The ${meta.label.toLowerCase()} photo is larger than the 10 MB upload limit. Please retake it.`,
        `Slot "${slot}" is ${image.sizeBytes} bytes.`,
      );
    }

    const part = toFilePart(image, meta.field.replace(/_/g, '-'));

    // React Native's FormData takes `(key, { uri, name, type })` and builds
    // the multipart file part — plus the boundary — itself. The DOM typings
    // only allow Blob/string, hence the cast. The web-only third `filename`
    // argument is deliberately omitted: RN ignores it and the name is already
    // carried by `part.name`.
    form.append(meta.field, part as unknown as Blob);
  }

  return form;
}

/**
 * Submits the captured bundle for screening.
 *
 * @throws {@link ApiError} for configuration, validation, network, timeout,
 *         HTTP and malformed-response failures.
 */
export async function submitScreening(
  captures: CaptureBundle,
  options: RequestOptions = {},
): Promise<ScreeningResponse> {
  const form = buildScreeningFormData(captures);
  const raw = await postFormData<unknown>(SCREEN_ENDPOINT, form, options);
  return normaliseScreeningResponse(raw);
}

/* ------------------------------------------------------------------ */
/* Response normalisation                                              */
/* ------------------------------------------------------------------ */

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function asNullableString(value: unknown): string | null {
  const s = asString(value);
  return s !== null && s.trim().length > 0 ? s : null;
}

/**
 * Validates only what the UI depends on structurally, and keeps `status` as
 * whatever string the server sent so a future status is displayed as
 * "needs review" rather than crashing or being read as a pass.
 */
export function normaliseScreeningResponse(raw: unknown): ScreeningResponse {
  if (!isRecord(raw)) {
    throw malformedResponseError('Screening response was not a JSON object.');
  }

  const status = asString(raw.status);
  if (status === null || status.trim().length === 0) {
    throw malformedResponseError('Screening response had no "status" field.');
  }

  return {
    screening_id: asString(raw.screening_id) ?? '',
    status: status.trim(),
    student: normaliseStudent(raw.student),
    face_verification: normaliseFaceVerification(raw.face_verification),
    message: asString(raw.message) ?? '',
  };
}

function normaliseStudent(raw: unknown): StudentSummary | null {
  if (!isRecord(raw)) return null;

  return {
    student_id: asString(raw.student_id) ?? '',
    name: asString(raw.name) ?? '',
    course: asNullableString(raw.course),
    college: asNullableString(raw.college),
    dob: asNullableString(raw.dob),
    valid_till: asNullableString(raw.valid_till),
    status: asString(raw.status) ?? '',
    blacklisted: raw.blacklisted === true,
  };
}

function normaliseFaceVerification(raw: unknown): FaceVerificationResult | null {
  if (!isRecord(raw)) return null;

  // `confidence` is a cosine similarity (0.0–1.0) — kept exactly as sent, and
  // never rescaled into a percentage.
  const confidence = typeof raw.confidence === 'number' ? raw.confidence : Number.NaN;

  return {
    match: raw.match === true,
    confidence,
  };
}
