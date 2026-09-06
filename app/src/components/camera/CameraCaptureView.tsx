import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, Platform, StyleSheet, View } from 'react-native';
import { CameraType, CameraView, useCameraPermissions } from 'expo-camera';

import { colors, spacing } from '../../theme';
import { Text } from '../Text';
import { CameraPermissionGate, PermissionPhase } from './CameraPermissionGate';
import { FramingGuide, GuideShape } from './FramingGuide';
import { ShutterBar } from './ShutterBar';
import { useCameraAvailability } from '../../hooks/useCameraAvailability';

export interface CameraShot {
  uri: string;
  width: number;
  height: number;
  /** 'jpg' | 'png' as reported by expo-camera. */
  format: 'jpg' | 'png';
  /** Which lens actually took the shot (may differ after a flip). */
  facing: CameraType;
}

interface CameraCaptureViewProps {
  /** Which physical camera to open first. */
  facing: CameraType;
  /** Framing overlay shape. */
  guide: GuideShape;
  /** Short line shown under the cut-out. */
  hint?: string;
  /** Label read out for the shutter button. */
  captureLabel: string;
  /** Allow flipping between front/back. */
  allowFlip?: boolean;
  /** Pause the preview (e.g. while a captured image is being reviewed). */
  paused?: boolean;
  onCaptured: (shot: CameraShot) => void;
  onCancel: () => void;
}

/**
 * How long to wait for `onCameraReady` before telling the user the preview is
 * taking unusually long. The shutter stays disabled either way — this only
 * replaces an indefinite "Starting camera…" with something actionable.
 */
const READY_TIMEOUT_MS = 8_000;

/**
 * Turns any camera exception into one short, user-facing sentence.
 *
 * Native camera errors are terse and device-specific (`Camera is not running`,
 * `Session has been closed`), so they are mapped to plain language instead of
 * being shown verbatim.
 */
function describeCaptureFailure(error: unknown): string {
  const raw = error instanceof Error ? error.message : typeof error === 'string' ? error : '';
  const text = raw.toLowerCase();

  if (text.includes('permission') || text.includes('denied')) {
    return 'Camera access was lost. Please allow camera permission and try again.';
  }
  if (text.includes('unmount') || text.includes('closed') || text.includes('not running')) {
    return 'The camera stopped before the photo was taken. Please try again.';
  }
  if (text.includes('empty') || text.includes('no image')) {
    return 'The camera returned an empty photo. Please try again.';
  }
  if (text.includes('busy') || text.includes('in use')) {
    return 'The camera is busy. Close other apps using it and try again.';
  }
  if (text.includes('space') || text.includes('storage')) {
    return 'There is not enough free space to hold the photo. Free some space and try again.';
  }

  return 'The photo could not be taken. Hold the device steady and try again.';
}

/**
 * Real device camera preview with framing overlay and shutter.
 *
 * Owns the whole permission lifecycle so callers only deal with the captured
 * image. No image is written anywhere by this component — the URI returned by
 * expo-camera points at the app's own cache directory.
 */
export function CameraCaptureView({
  facing,
  guide,
  hint,
  captureLabel,
  allowFlip = false,
  paused = false,
  onCaptured,
  onCancel,
}: CameraCaptureViewProps) {
  const cameraRef = useRef<CameraView | null>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const availability = useCameraAvailability();

  const [currentFacing, setCurrentFacing] = useState<CameraType>(facing);
  const [ready, setReady] = useState(false);
  const [slowToStart, setSlowToStart] = useState(false);
  const [busy, setBusy] = useState(false);
  const [mountError, setMountError] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [appActive, setAppActive] = useState(AppState.currentState === 'active');
  /** Bumping this remounts `CameraView` after a mount failure. */
  const [mountAttempt, setMountAttempt] = useState(0);
  const [requestingPermission, setRequestingPermission] = useState(false);

  /** Prevents state updates (and duplicate shots) after unmount. */
  const mounted = useRef(true);
  /** Synchronous re-entrancy guard: `busy` state lands a render too late. */
  const capturing = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // Follow the requested facing if the caller changes slot without unmounting.
  useEffect(() => {
    setCurrentFacing(facing);
  }, [facing]);

  // Release the camera while the app is backgrounded.
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (mounted.current) setAppActive(state === 'active');
    });
    return () => sub.remove();
  }, []);

  // A remount or a lens switch means the preview has to warm up again.
  useEffect(() => {
    setReady(false);
    setSlowToStart(false);
  }, [currentFacing, mountAttempt]);

  // Surface a stuck initialisation instead of an endless spinner.
  useEffect(() => {
    if (ready || mountError) return;

    const timer = setTimeout(() => {
      if (mounted.current) setSlowToStart(true);
    }, READY_TIMEOUT_MS);

    return () => clearTimeout(timer);
  }, [ready, mountError, mountAttempt, currentFacing]);

  const handleCapture = useCallback(async () => {
    const camera = cameraRef.current;

    if (!camera) {
      setCaptureError('The camera is not ready yet. Please wait a moment and try again.');
      return;
    }
    if (capturing.current) return;

    capturing.current = true;
    setBusy(true);
    setCaptureError(null);

    try {
      const photo = await camera.takePictureAsync({
        quality: 0.85,
        // Keep orientation processing on so the saved image matches the
        // preview on devices that report frames rotated.
        skipProcessing: false,
        imageType: 'jpg',
      });

      // The screen may have been left while the shutter was working; dropping
      // the shot here avoids updating an unmounted tree.
      if (!mounted.current) return;

      if (!photo || typeof photo.uri !== 'string' || photo.uri.trim().length === 0) {
        throw new Error('The camera returned an empty image.');
      }

      onCaptured({
        uri: photo.uri,
        width: typeof photo.width === 'number' ? photo.width : 0,
        height: typeof photo.height === 'number' ? photo.height : 0,
        format: photo.format === 'png' ? 'png' : 'jpg',
        facing: currentFacing,
      });
    } catch (error) {
      if (mounted.current) {
        setCaptureError(describeCaptureFailure(error));
      }
    } finally {
      capturing.current = false;
      if (mounted.current) setBusy(false);
    }
  }, [currentFacing, onCaptured]);

  const askForPermission = useCallback(async () => {
    if (requestingPermission) return;

    setRequestingPermission(true);
    try {
      await requestPermission();
    } catch {
      // A rejected permission request is not an error state of its own: the
      // gate re-renders from the (unchanged) permission object below.
    } finally {
      if (mounted.current) setRequestingPermission(false);
    }
  }, [requestPermission, requestingPermission]);

  const retryMount = useCallback(() => {
    setMountError(null);
    setCaptureError(null);
    setMountAttempt((n) => n + 1);
  }, []);

  // ---- Non-preview states -------------------------------------------------

  if (availability === 'unavailable') {
    return (
      <CameraPermissionGate
        phase="unavailable"
        onRequest={() => {}}
        onCancel={onCancel}
        errorMessage="This device or browser exposes no camera input."
      />
    );
  }

  if (mountError) {
    return (
      <CameraPermissionGate
        phase="failed"
        onRequest={retryMount}
        onCancel={onCancel}
        errorMessage={mountError}
      />
    );
  }

  if (!permission || availability === 'checking') {
    return <CameraPermissionGate phase="checking" onRequest={() => {}} onCancel={onCancel} />;
  }

  if (!permission.granted) {
    const phase: PermissionPhase = permission.canAskAgain
      ? permission.status === 'denied'
        ? 'denied'
        : 'undetermined'
      : 'blocked';

    return (
      <CameraPermissionGate
        phase={phase}
        busy={requestingPermission}
        onRequest={() => {
          void askForPermission();
        }}
        onCancel={onCancel}
      />
    );
  }

  // ---- Live preview -------------------------------------------------------

  const active = appActive && !paused;

  return (
    <View style={styles.root}>
      <View style={styles.previewWrapper}>
        <CameraView
          key={`${currentFacing}-${mountAttempt}`}
          ref={cameraRef}
          style={StyleSheet.absoluteFill}
          facing={currentFacing}
          mode="picture"
          active={active}
          animateShutter={false}
          autofocus="off"
          onCameraReady={() => {
            if (mounted.current) {
              setReady(true);
              setSlowToStart(false);
            }
          }}
          onMountError={(event) => {
            if (mounted.current) {
              setMountError(
                event?.message ??
                  'The camera could not be started on this device.',
              );
            }
          }}
        />

        <FramingGuide shape={guide} hint={hint} active={busy} />

        {!ready ? (
          <View style={styles.loading} accessibilityLiveRegion="polite">
            <Text variant="body" tone="inverse" center>
              {slowToStart ? 'Camera is taking longer than usual' : 'Starting camera…'}
            </Text>
            {slowToStart ? (
              <Text variant="caption" tone="inverseMuted" center style={styles.loadingHint}>
                Make sure no other app is using the camera. You can go back and try this step
                again.
              </Text>
            ) : null}
          </View>
        ) : null}

        {/* Backgrounding releases the camera, so say so rather than showing a
            frozen frame with a live-looking shutter. */}
        {ready && !active ? (
          <View style={styles.loading} accessibilityLiveRegion="polite">
            <Text variant="body" tone="inverse" center>
              Camera paused
            </Text>
            <Text variant="caption" tone="inverseMuted" center style={styles.loadingHint}>
              Return to the app to continue capturing.
            </Text>
          </View>
        ) : null}
      </View>

      {captureError ? (
        <View style={styles.errorBar} accessibilityRole="alert" accessibilityLiveRegion="assertive">
          <Text variant="caption" tone="inverse" center>
            {captureError}
          </Text>
        </View>
      ) : null}

      <ShutterBar
        captureLabel={captureLabel}
        busy={busy}
        disabled={!ready || !active}
        onCapture={() => {
          void handleCapture();
        }}
        onCancel={onCancel}
        onFlip={
          allowFlip
            ? () => {
                setCaptureError(null);
                setCurrentFacing((prev) => (prev === 'back' ? 'front' : 'back'));
              }
            : undefined
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.surfaceDark,
  },
  previewWrapper: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: Platform.OS === 'android' ? '#000000' : colors.surfaceDark,
  },
  loading: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xxl,
    gap: spacing.xs,
    backgroundColor: colors.surfaceDark,
  },
  loadingHint: {
    maxWidth: 300,
  },
  errorBar: {
    backgroundColor: colors.danger,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
});
