/**
 * A single error type for every failure mode of the screening request, so the
 * UI can render one understandable message plus an honest retry affordance.
 *
 * Raw exceptions and stack traces are never shown to the user; `message` is
 * always user-facing copy, while `detail` keeps the technical cause for logs.
 */

export type ApiErrorKind =
  /** No / invalid EXPO_PUBLIC_API_BASE_URL. */
  | 'config'
  /** Nothing was captured, or a file is unusable before upload. */
  | 'invalid_input'
  /** Request never reached the server (offline, DNS, refused, TLS). */
  | 'network'
  /** Server did not answer within the timeout. */
  | 'timeout'
  /** Aborted deliberately (user cancelled / screen unmounted). */
  | 'cancelled'
  /** Server answered with a non-2xx status. */
  | 'http'
  /** 2xx body was not JSON, or not the documented shape. */
  | 'malformed_response';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  /** HTTP status code, when the failure came from a response. */
  readonly status?: number;
  /** Technical cause, for console logging only. */
  readonly detail?: string;
  /** True when trying the exact same request again could plausibly succeed. */
  readonly retryable: boolean;

  constructor(args: {
    kind: ApiErrorKind;
    message: string;
    status?: number;
    detail?: string;
    retryable?: boolean;
  }) {
    super(args.message);
    this.name = 'ApiError';
    this.kind = args.kind;
    this.status = args.status;
    this.detail = args.detail;
    this.retryable = args.retryable ?? DEFAULT_RETRYABLE[args.kind];
  }
}

const DEFAULT_RETRYABLE: Record<ApiErrorKind, boolean> = {
  config: false,
  invalid_input: false,
  network: true,
  timeout: true,
  cancelled: true,
  http: true,
  malformed_response: true,
};

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** Anything thrown that is not already an ApiError becomes an unexpected one. */
export function toApiError(cause: unknown): ApiError {
  if (isApiError(cause)) return cause;

  const detail = cause instanceof Error ? `${cause.name}: ${cause.message}` : String(cause);

  return new ApiError({
    kind: 'network',
    message: 'Something went wrong while contacting the screening server. Please try again.',
    detail,
  });
}

/* ------------------------------------------------------------------ */
/* Factories — one place for all user-facing wording                   */
/* ------------------------------------------------------------------ */

export function configError(detail?: string): ApiError {
  return new ApiError({
    kind: 'config',
    message:
      'This app has no screening server address configured, so nothing can be submitted. ' +
      'Set EXPO_PUBLIC_API_BASE_URL and restart the app.',
    detail,
  });
}

export function invalidInputError(message: string, detail?: string): ApiError {
  return new ApiError({ kind: 'invalid_input', message, detail });
}

export function networkError(detail?: string): ApiError {
  return new ApiError({
    kind: 'network',
    message:
      'Could not reach the screening server. Check your internet connection and that the ' +
      'server address is correct, then try again.',
    detail,
  });
}

export function timeoutError(timeoutMs: number): ApiError {
  const seconds = Math.round(timeoutMs / 1000);
  return new ApiError({
    kind: 'timeout',
    message: `The screening server did not respond within ${seconds} seconds. Please try again.`,
    detail: `Aborted after ${timeoutMs}ms.`,
  });
}

export function cancelledError(): ApiError {
  return new ApiError({
    kind: 'cancelled',
    message: 'Screening was cancelled before it finished.',
  });
}

export function malformedResponseError(detail?: string): ApiError {
  return new ApiError({
    kind: 'malformed_response',
    message:
      'The screening server replied in a format this app could not read, so no result can be ' +
      'shown. Please try again.',
    detail,
  });
}

/**
 * Maps an HTTP status (plus FastAPI's optional `{"detail": "..."}`) onto
 * user-facing copy. Server text is only appended when it is short enough to
 * read comfortably, so raw tracebacks never leak into the UI.
 */
export function httpError(status: number, serverDetail?: string): ApiError {
  const base = describeStatus(status);
  const hint = readableServerDetail(serverDetail);

  return new ApiError({
    kind: 'http',
    status,
    message: hint ? `${base} (${hint})` : base,
    detail: serverDetail,
    retryable: status >= 500 || status === 408 || status === 429,
  });
}

function describeStatus(status: number): string {
  switch (status) {
    case 400:
      return 'The server rejected the submission because the photos were not usable. Please retake them and try again.';
    case 401:
    case 403:
      return 'This app is not authorised to use the screening service. Please contact the operator.';
    case 404:
      return 'The screening endpoint was not found at the configured server address. Please check the configuration.';
    case 408:
      return 'The server closed the request before it completed. Please try again.';
    case 413:
      return 'The photos are too large to upload. Each image must be under 10 MB — please retake them.';
    case 415:
      return 'The server does not accept this image format. Only JPG and PNG photos can be screened.';
    case 422:
      return 'The server could not process the submitted photos. Please retake all three and try again.';
    case 429:
      return 'Too many screening requests have been sent. Please wait a moment and try again.';
    case 503:
    case 504:
      return 'The screening service is temporarily unavailable. Please try again in a moment.';
    default:
      break;
  }

  if (status >= 500) {
    return 'The screening service hit an internal error and could not finish. Please try again in a moment.';
  }

  return `The screening server refused the request (HTTP ${status}).`;
}

const MAX_SERVER_DETAIL_CHARS = 160;

function readableServerDetail(detail?: string): string | null {
  if (typeof detail !== 'string') return null;

  const cleaned = detail.replace(/\s+/g, ' ').trim();
  if (cleaned.length === 0) return null;
  if (cleaned.length > MAX_SERVER_DETAIL_CHARS) return null;
  // Never surface anything that looks like a stack trace.
  if (/Traceback|at .+\(.+:\d+:\d+\)/i.test(cleaned)) return null;

  return cleaned;
}
