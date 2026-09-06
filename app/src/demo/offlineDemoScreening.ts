import type { CaptureBundle } from '../types/screening';
import type { ScreeningResponse } from '../types/screening';
import { ApiError } from '../api/errors';

export type DemoStage =
  | 'preparing'
  | 'documents'
  | 'identity'
  | 'complete';

export const DEMO_STAGE_ORDER: readonly DemoStage[] = [
  'preparing',
  'documents',
  'identity',
  'complete',
];

export const DEMO_STAGE_COPY: Record<DemoStage, string> = {
  preparing: 'Preparing verification...',
  documents: 'Analyzing captured documents...',
  identity: 'Checking identity...',
  complete: 'Verification complete',
};

export interface OfflineDemoOptions {
  signal?: AbortSignal;
  onStage?: (stage: DemoStage) => void;
}

const DEMO_DELAY_MS = 350;

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw new ApiError({
      kind: 'cancelled',
      message: 'Verification was cancelled.',
      retryable: false,
    });
  }
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(
        new ApiError({
          kind: 'cancelled',
          message: 'Verification was cancelled.',
          retryable: false,
        }),
      );
      return;
    }

    const timer = setTimeout(resolve, ms);

    const handleAbort = () => {
      clearTimeout(timer);
      reject(
        new ApiError({
          kind: 'cancelled',
          message: 'Verification was cancelled.',
          retryable: false,
        }),
      );
    };

    signal?.addEventListener('abort', handleAbort, { once: true });
  });
}

/**
 * Deterministic local result for demonstrations only.
 *
 * This does NOT perform OCR, face recognition, tamper detection, or any other
 * genuine identity-verification algorithm.
 */
export async function runOfflineDemoScreening(
  captures: CaptureBundle,
  options: OfflineDemoOptions = {},
): Promise<ScreeningResponse> {
  const { signal, onStage } = options;

  if (
    !captures.documentFront ||
    !captures.documentBack ||
    !captures.livePhoto
  ) {
    throw new ApiError({
      kind: 'local_processing',
      message: 'All three required captures are needed before verification.',
      retryable: false,
    });
  }

  throwIfAborted(signal);

  onStage?.('preparing');
  await wait(DEMO_DELAY_MS, signal);

  throwIfAborted(signal);

  onStage?.('documents');
  await wait(DEMO_DELAY_MS, signal);

  throwIfAborted(signal);

  onStage?.('identity');
  await wait(DEMO_DELAY_MS, signal);

  throwIfAborted(signal);

  onStage?.('complete');

  return {
    screening_id: `DEMO-${Date.now()}`,
    status: 'completed',
    student: {
      student_id: 'DEMO-STUDENT-001',
      name: 'Demo Student',
      course: 'Demo Verification',
      college: 'Smart India Hackathon',
      dob: null,
      valid_till: null,
      status: 'active',
      blacklisted: false,
    },
    face_verification: {
      match: true,
      confidence: 0.87,
    },
    message: 'Offline demonstration result. No backend verification was performed.',
  };
}
