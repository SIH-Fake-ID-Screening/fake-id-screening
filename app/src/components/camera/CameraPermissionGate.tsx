import React from 'react';
import { ActivityIndicator, Linking, Platform, StyleSheet, View } from 'react-native';

import { colors, spacing } from '../../theme';
import { Button } from '../Button';
import { Text } from '../Text';

export type PermissionPhase =
  /** Still resolving permission / hardware availability. */
  | 'checking'
  /** Permission has not been asked for yet. */
  | 'undetermined'
  /** The user declined, but the OS will let us ask again. */
  | 'denied'
  /** Turned off in system settings; only Settings can change it. */
  | 'blocked'
  /** No usable camera on this device/browser. */
  | 'unavailable'
  /** A camera exists but failed to initialise; retrying may work. */
  | 'failed';

interface CameraPermissionGateProps {
  phase: PermissionPhase;
  /** Requests the OS permission again, or retries camera start-up. */
  onRequest: () => void;
  /** Leaves the camera step. */
  onCancel: () => void;
  /** Extra detail for the `unavailable` / `failed` phases. */
  errorMessage?: string | null;
  /** Shows a spinner on the primary action (e.g. permission dialog open). */
  busy?: boolean;
}

const COPY: Record<Exclude<PermissionPhase, 'checking'>, { title: string; body: string }> = {
  undetermined: {
    title: 'Camera access needed',
    body: 'VerifID needs your camera to photograph your ID card and take a live selfie. The images stay on this device until you submit them.',
  },
  denied: {
    title: 'Camera permission was declined',
    body: 'Without camera access the photos cannot be captured. You can grant permission and try again.',
  },
  blocked: {
    title: 'Camera blocked in system settings',
    body:
      Platform.OS === 'ios'
        ? 'Open Settings → VerifID and turn on Camera, then come back to this screen.'
        : 'Open app settings → Permissions and allow Camera, then come back to this screen.',
  },
  unavailable: {
    title: 'Camera unavailable',
    body: 'No usable camera was found on this device, so this step cannot be completed here.',
  },
  failed: {
    title: 'Camera could not start',
    body: 'The camera did not start up correctly. This is usually temporary — try again, or close other apps that may be using the camera.',
  },
};

/**
 * Full-screen state shown whenever a real preview cannot be rendered:
 * permission still to be asked, refused, blocked in settings, no camera, or a
 * failed initialisation. The user always has a next action — never a blank
 * camera screen and never a raw error string on its own.
 */
export function CameraPermissionGate({
  phase,
  onRequest,
  onCancel,
  errorMessage,
  busy = false,
}: CameraPermissionGateProps) {
  if (phase === 'checking') {
    return (
      <View style={styles.root} accessibilityLiveRegion="polite">
        <View style={styles.body}>
          <ActivityIndicator size="large" color={colors.textInverse} />
          <Text variant="body" tone="inverseMuted" center>
            Preparing the camera…
          </Text>
        </View>
      </View>
    );
  }

  const copy = COPY[phase];
  const canRequestPermission = phase === 'undetermined' || phase === 'denied';
  const canRetryCamera = phase === 'failed';
  // Technical detail is a secondary line, never the headline.
  const showDetail =
    typeof errorMessage === 'string' &&
    errorMessage.trim().length > 0 &&
    (phase === 'unavailable' || phase === 'failed');

  return (
    <View style={styles.root}>
      <View style={styles.body}>
        <Text style={styles.glyph} accessibilityElementsHidden>
          📷
        </Text>
        <Text variant="title" tone="inverse" center accessibilityRole="header">
          {copy.title}
        </Text>
        <Text variant="body" tone="inverseMuted" center>
          {copy.body}
        </Text>
        {showDetail ? (
          <Text variant="caption" tone="inverseMuted" center style={styles.detail}>
            {errorMessage?.trim()}
          </Text>
        ) : null}
      </View>

      <View style={styles.actions}>
        {canRequestPermission ? (
          <Button
            label={phase === 'denied' ? 'Try again' : 'Allow camera access'}
            loading={busy}
            onPress={onRequest}
            accessibilityHint="Asks the operating system for camera permission"
          />
        ) : null}

        {canRetryCamera ? (
          <Button
            label="Retry camera"
            icon="↻"
            onPress={onRequest}
            accessibilityHint="Starts the camera again"
          />
        ) : null}

        {phase === 'blocked' ? (
          <Button
            label="Open settings"
            onPress={() => {
              void Linking.openSettings();
            }}
            accessibilityHint="Opens the system settings for this app"
          />
        ) : null}

        <Button
          label="Go back"
          variant="ghost"
          onPress={onCancel}
          accessibilityHint="Leaves this capture step"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.surfaceDark,
    justifyContent: 'center',
    paddingHorizontal: spacing.xxl,
    paddingVertical: spacing.xxxl,
    gap: spacing.xxl,
  },
  body: {
    gap: spacing.md,
    alignItems: 'center',
  },
  glyph: {
    fontSize: 40,
    marginBottom: spacing.sm,
  },
  detail: {
    maxWidth: 320,
  },
  actions: {
    gap: spacing.sm,
  },
});
