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
 * Real device camera preview with framing overlay and shutter.
 *
 * Owns the whole permission lifecycle so callers only deal with the
 * captured image. No image is written anywhere by this component — the URI
 * returned by expo-camera points at the app's own cache directory.
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
  const [busy, setBusy] = useState(false);
  const [mountError, setMountError] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [appActive, setAppActive] = useState(AppState.currentState === 'active');

  // Follow the requested facing if the caller changes slot without unmounting.
  useEffect(() => {
    setCurrentFacing(facing);
  }, [facing]);

  // Release the camera while the app is backgrounded.
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      setAppActive(state === 'active');
    });
    return () => sub.remove();
  }, []);

  const handleCapture = useCallback(async () => {
    const camera = cameraRef.current;
    if (!camera || busy) {
      return;
    }

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

      if (!photo?.uri) {
        throw new Error('The camera returned an empty image.');
      }

      onCaptured({
        uri: photo.uri,
        width: photo.width,
        height: photo.height,
        format: photo.format ?? 'jpg',
        facing: currentFacing,
      });
    } catch (error) {
      setCaptureError(
        error instanceof Error && error.message
          ? error.message
          : 'The photo could not be taken. Please try again.',
      );
    } finally {
      setBusy(false);
    }
  }, [busy, currentFacing, onCaptured]);

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
        phase="unavailable"
        onRequest={() => {}}
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
        onRequest={() => {
          void requestPermission();
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
          ref={cameraRef}
          style={StyleSheet.absoluteFill}
          facing={currentFacing}
          mode="picture"
          active={active}
          animateShutter={false}
          autofocus="off"
          onCameraReady={() => setReady(true)}
          onMountError={(event) =>
            setMountError(event?.message ?? 'The camera could not be started.')
          }
        />

        <FramingGuide shape={guide} hint={hint} active={busy} />

        {!ready ? (
          <View style={styles.loading} accessibilityLiveRegion="polite">
            <Text variant="caption" tone="inverseMuted">
              Starting camera…
            </Text>
          </View>
        ) : null}
      </View>

      {captureError ? (
        <View style={styles.errorBar} accessibilityLiveRegion="polite">
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
            ? () => setCurrentFacing((prev) => (prev === 'back' ? 'front' : 'back'))
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
    backgroundColor: colors.surfaceDark,
  },
  errorBar: {
    backgroundColor: colors.danger,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
});
