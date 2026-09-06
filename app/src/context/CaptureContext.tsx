import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

import { CAPTURE_ORDER } from '../constants/captureSlots';
import type { CaptureBundle, CapturedImage, CaptureSlot } from '../types/screening';

const EMPTY_BUNDLE: CaptureBundle = {
  documentFront: null,
  documentBack: null,
  livePhoto: null,
};

interface CaptureContextValue {
  captures: CaptureBundle;
  /** Store (or replace) the image for a slot. */
  setCapture: (slot: CaptureSlot, image: CapturedImage) => void;
  /** Discard the image for a slot so it can be retaken. */
  clearCapture: (slot: CaptureSlot) => void;
  /** Discard everything — used when starting a fresh verification. */
  reset: () => void;
  /** True when all three required images are present. */
  isComplete: boolean;
  /** Number of slots filled. */
  completedCount: number;
  /** The next slot that still needs an image, or null when complete. */
  nextIncompleteSlot: CaptureSlot | null;
}

const CaptureContext = createContext<CaptureContextValue | null>(null);

/**
 * Holds the three captured images for the duration of one verification.
 *
 * Deliberately in-memory only: ID photos and selfies are sensitive, so they
 * are never persisted to disk by the app and are dropped when the flow resets.
 */
export function CaptureProvider({ children }: { children: React.ReactNode }) {
  const [captures, setCaptures] = useState<CaptureBundle>(EMPTY_BUNDLE);

  const setCapture = useCallback((slot: CaptureSlot, image: CapturedImage) => {
    setCaptures((prev) => ({ ...prev, [slot]: image }));
  }, []);

  const clearCapture = useCallback((slot: CaptureSlot) => {
    setCaptures((prev) => ({ ...prev, [slot]: null }));
  }, []);

  const reset = useCallback(() => {
    setCaptures(EMPTY_BUNDLE);
  }, []);

  const value = useMemo<CaptureContextValue>(() => {
    const completedCount = CAPTURE_ORDER.filter((slot) => captures[slot] !== null).length;
    const nextIncompleteSlot = CAPTURE_ORDER.find((slot) => captures[slot] === null) ?? null;

    return {
      captures,
      setCapture,
      clearCapture,
      reset,
      isComplete: completedCount === CAPTURE_ORDER.length,
      completedCount,
      nextIncompleteSlot,
    };
  }, [captures, setCapture, clearCapture, reset]);

  return <CaptureContext.Provider value={value}>{children}</CaptureContext.Provider>;
}

export function useCaptures(): CaptureContextValue {
  const ctx = useContext(CaptureContext);
  if (!ctx) {
    throw new Error('useCaptures must be used inside a <CaptureProvider>.');
  }
  return ctx;
}
