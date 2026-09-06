import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { submitScreening } from '../api/screening';
import { ApiError, toApiError } from '../api/errors';
import { isApiConfigured } from '../config/env';
import { useCaptures } from './CaptureContext';
import type { ScreeningResponse } from '../types/screening';

export type SubmissionPhase = 'idle' | 'submitting' | 'succeeded' | 'failed';

/** Outcome of calling {@link ScreeningContextValue.submit}. */
export type SubmitOutcome =
  /** The request was sent and a real backend result came back. */
  | { kind: 'result'; result: ScreeningResponse }
  /** The attempt failed; `error` is user-presentable. */
  | { kind: 'error'; error: ApiError }
  /** The user (or an unmount) aborted the request. */
  | { kind: 'cancelled' }
  /** A request was already in flight, so this call did nothing. */
  | { kind: 'duplicate' };

interface ScreeningContextValue {
  phase: SubmissionPhase;
  /** True while the multipart upload / screening request is in flight. */
  isSubmitting: boolean;
  /** The real backend response, once one has been received. */
  result: ScreeningResponse | null;
  /** The last failure, as user-presentable copy plus a technical detail. */
  error: ApiError | null;
  /** Whether the app has a server address configured at all. */
  isConfigured: boolean;
  /** True when the previous attempt was aborted rather than failing. */
  wasCancelled: boolean;
  /**
   * Uploads the three captured images. Resolves with a tagged outcome so
   * callers can tell a genuine failure from a duplicate call or a
   * cancellation. Calling while a request is in flight is a no-op.
   */
  submit: () => Promise<SubmitOutcome>;
  /** Aborts an in-flight request (e.g. the user cancels). */
  cancel: () => void;
  /** Clears result/error so the flow can be run again. */
  reset: () => void;
}

const ScreeningContext = createContext<ScreeningContextValue | null>(null);

/**
 * Owns the single `POST /api/v1/screen` request for one verification attempt.
 *
 * The request lives here rather than inside a screen so that moving from
 * Review to the Processing screen cannot cancel it or drop the response, and
 * so a failed attempt can be retried with the images already in
 * `CaptureContext` — no recapture required.
 *
 * There is no mock/offline path: if the backend is unreachable, the failure is
 * surfaced as-is and no result is produced.
 */
export function ScreeningProvider({ children }: { children: React.ReactNode }) {
  const { captures } = useCaptures();

  const [phase, setPhase] = useState<SubmissionPhase>('idle');
  const [result, setResult] = useState<ScreeningResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [wasCancelled, setWasCancelled] = useState(false);

  /** Guards against duplicate submissions without waiting for a re-render. */
  const inFlight = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledByUser = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      // Never leave a request running against a torn-down tree.
      abortRef.current?.abort();
      abortRef.current = null;
      inFlight.current = false;
    };
  }, []);

  const submit = useCallback(async (): Promise<SubmitOutcome> => {
    // Synchronous guard: two rapid taps cannot both start an upload.
    if (inFlight.current) return { kind: 'duplicate' };

    inFlight.current = true;
    cancelledByUser.current = false;

    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('submitting');
    setError(null);
    setResult(null);
    setWasCancelled(false);

    try {
      const response = await submitScreening(captures, { signal: controller.signal });

      if (!mounted.current) return { kind: 'result', result: response };

      setResult(response);
      setPhase('succeeded');
      return { kind: 'result', result: response };
    } catch (cause) {
      const apiError = toApiError(cause);

      if (__DEV__) {
        // Detail stays in the console; the UI only shows `message`.
        console.warn(
          '[screening] submission failed',
          apiError.kind,
          apiError.detail ?? apiError.message,
        );
      }

      // A deliberate abort is not a failure: it returns the flow to Review
      // with the captures intact and no alarming error banner.
      const aborted = apiError.kind === 'cancelled' || cancelledByUser.current;

      if (mounted.current) {
        if (aborted) {
          setPhase('idle');
          setError(null);
          setWasCancelled(true);
        } else {
          setError(apiError);
          setPhase('failed');
        }
      }

      return aborted ? { kind: 'cancelled' } : { kind: 'error', error: apiError };
    } finally {
      inFlight.current = false;
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [captures]);

  const cancel = useCallback(() => {
    if (!inFlight.current) return;
    cancelledByUser.current = true;
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    inFlight.current = false;
    cancelledByUser.current = false;
    setPhase('idle');
    setResult(null);
    setError(null);
    setWasCancelled(false);
  }, []);

  const value = useMemo<ScreeningContextValue>(
    () => ({
      phase,
      isSubmitting: phase === 'submitting',
      result,
      error,
      isConfigured: isApiConfigured(),
      wasCancelled,
      submit,
      cancel,
      reset,
    }),
    [phase, result, error, wasCancelled, submit, cancel, reset],
  );

  return <ScreeningContext.Provider value={value}>{children}</ScreeningContext.Provider>;
}

export function useScreening(): ScreeningContextValue {
  const ctx = useContext(ScreeningContext);
  if (!ctx) {
    throw new Error('useScreening must be used inside a <ScreeningProvider>.');
  }
  return ctx;
}
