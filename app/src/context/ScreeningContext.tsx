import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { submitScreening } from '../api/screening';
import { ApiError, toApiError } from '../api/errors';
import { isApiConfigured } from '../config/env';
import { useCaptures } from './CaptureContext';
import type { ScreeningResponse } from '../types/screening';

export type SubmissionPhase = 'idle' | 'submitting' | 'succeeded' | 'failed';

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
  /**
   * Uploads the three captured images. Resolves with the backend response, or
   * `null` when the attempt failed (the failure is exposed via `error`).
   * Calling while a request is in flight is a no-op.
   */
  submit: () => Promise<ScreeningResponse | null>;
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

  /** Guards against duplicate submissions without waiting for a re-render. */
  const inFlight = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const submit = useCallback(async (): Promise<ScreeningResponse | null> => {
    if (inFlight.current) return null;

    inFlight.current = true;
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('submitting');
    setError(null);
    setResult(null);

    try {
      const response = await submitScreening(captures, { signal: controller.signal });

      if (!mounted.current) return response;

      setResult(response);
      setPhase('succeeded');
      return response;
    } catch (cause) {
      const apiError = toApiError(cause);

      if (__DEV__) {
        // Detail stays in the console; the UI only shows `message`.
        console.warn('[screening] submission failed', apiError.kind, apiError.detail ?? apiError.message);
      }

      if (mounted.current) {
        setError(apiError);
        setPhase('failed');
      }
      return null;
    } finally {
      inFlight.current = false;
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [captures]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    inFlight.current = false;
    setPhase('idle');
    setResult(null);
    setError(null);
  }, []);

  const value = useMemo<ScreeningContextValue>(
    () => ({
      phase,
      isSubmitting: phase === 'submitting',
      result,
      error,
      isConfigured: isApiConfigured(),
      submit,
      cancel,
      reset,
    }),
    [phase, result, error, submit, cancel, reset],
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
