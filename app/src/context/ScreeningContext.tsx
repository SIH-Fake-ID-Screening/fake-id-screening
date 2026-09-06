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
import { resolveScreeningMode, type ScreeningMode } from '../config/demoMode';
import { runOfflineDemoScreening, type DemoStage } from '../demo/offlineDemoScreening';
import { useCaptures } from './CaptureContext';
import type { ScreeningResponse } from '../types/screening';

export type SubmissionPhase = 'idle' | 'submitting' | 'succeeded' | 'failed';

/** Outcome of calling {@link ScreeningContextValue.submit}. */
export type SubmitOutcome =
  /** The attempt produced a result (real backend, or offline demo). */
  | { kind: 'result'; result: ScreeningResponse }
  /** The attempt failed; `error` is user-presentable. */
  | { kind: 'error'; error: ApiError }
  /** The user (or an unmount) aborted the attempt. */
  | { kind: 'cancelled' }
  /** An attempt was already running, so this call did nothing. */
  | { kind: 'duplicate' };

interface ScreeningContextValue {
  phase: SubmissionPhase;
  /** True while a verification attempt is running. */
  isSubmitting: boolean;
  /** The result of the last attempt, once one has been produced. */
  result: ScreeningResponse | null;
  /** The last failure, as user-presentable copy plus a technical detail. */
  error: ApiError | null;
  /** Whether the app has a server address configured at all. */
  isConfigured: boolean;
  /** Which path a submission will take. */
  mode: ScreeningMode;
  /** Convenience flag for `mode === 'offline_demo'`. */
  isDemoMode: boolean;
  /**
   * Current stage of the offline demo run, for the Processing screen. Always
   * null in backend mode, which reports no progress.
   */
  demoStage: DemoStage | null;
  /** True when the previous attempt was aborted rather than failing. */
  wasCancelled: boolean;
  /**
   * Runs one verification attempt. Resolves with a tagged outcome so callers
   * can tell a genuine failure from a duplicate call or a cancellation.
   * Calling while an attempt is running is a no-op.
   */
  submit: () => Promise<SubmitOutcome>;
  /** Aborts a running attempt (e.g. the user cancels). */
  cancel: () => void;
  /** Clears result/error so the flow can be run again. */
  reset: () => void;
}

const ScreeningContext = createContext<ScreeningContextValue | null>(null);

/**
 * Owns one verification attempt, whichever path it takes.
 *
 * Two paths exist and exactly one is active for a given build:
 *
 *   offline_demo → `runOfflineDemoScreening` (on-device, no network at all)
 *   backend      → `POST /api/v1/screen`     (the real screening pipeline)
 *
 * The attempt lives here rather than inside a screen so that moving from
 * Review to Processing cannot cancel it or drop the outcome, and so a failed
 * attempt can be retried with the images already in `CaptureContext` — no
 * recapture required.
 *
 * In backend mode there is still no mock fallback: an unreachable server
 * surfaces the failure as-is and produces no result. In demo mode nothing is
 * uploaded and the result is a clearly labelled fixed demonstration outcome —
 * never presented as a real screening decision.
 */
export function ScreeningProvider({ children }: { children: React.ReactNode }) {
  const { captures } = useCaptures();

  const mode = useMemo<ScreeningMode>(() => resolveScreeningMode(), []);
  const isDemoMode = mode === 'offline_demo';

  const [phase, setPhase] = useState<SubmissionPhase>('idle');
  const [result, setResult] = useState<ScreeningResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [wasCancelled, setWasCancelled] = useState(false);
  const [demoStage, setDemoStage] = useState<DemoStage | null>(null);

  /** Guards against duplicate submissions without waiting for a re-render. */
  const inFlight = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledByUser = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      // Never leave an attempt running against a torn-down tree.
      abortRef.current?.abort();
      abortRef.current = null;
      inFlight.current = false;
    };
  }, []);

  const submit = useCallback(async (): Promise<SubmitOutcome> => {
    // Synchronous guard: two rapid taps cannot both start an attempt.
    if (inFlight.current) return { kind: 'duplicate' };

    inFlight.current = true;
    cancelledByUser.current = false;

    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('submitting');
    setError(null);
    setResult(null);
    setWasCancelled(false);
    setDemoStage(isDemoMode ? 'preparing' : null);

    try {
      const response = isDemoMode
        ? await runOfflineDemoScreening(captures, {
            signal: controller.signal,
            onStage: (stage) => {
              // A late stage callback from an abandoned run must not repaint
              // the screen of a newer one.
              if (mounted.current && abortRef.current === controller) {
                setDemoStage(stage);
              }
            },
          })
        : await submitScreening(captures, { signal: controller.signal });

      if (!mounted.current) return { kind: 'result', result: response };

      setResult(response);
      setPhase('succeeded');
      return { kind: 'result', result: response };
    } catch (cause) {
      const apiError = toApiError(cause);

      if (__DEV__) {
        // Detail stays in the console; the UI only shows `message`.
        console.warn(
          `[screening] ${mode} attempt failed`,
          apiError.kind,
          apiError.detail ?? apiError.message,
        );
      }

      // A deliberate abort is not a failure: it returns the flow to Review
      // with the captures intact and no alarming error banner.
      const aborted = apiError.kind === 'cancelled' || cancelledByUser.current;

      if (mounted.current) {
        setDemoStage(null);

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
  }, [captures, isDemoMode, mode]);

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
    setDemoStage(null);
  }, []);

  const value = useMemo<ScreeningContextValue>(
    () => ({
      phase,
      isSubmitting: phase === 'submitting',
      result,
      error,
      isConfigured: isApiConfigured(),
      mode,
      isDemoMode,
      demoStage,
      wasCancelled,
      submit,
      cancel,
      reset,
    }),
    [phase, result, error, mode, isDemoMode, demoStage, wasCancelled, submit, cancel, reset],
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
