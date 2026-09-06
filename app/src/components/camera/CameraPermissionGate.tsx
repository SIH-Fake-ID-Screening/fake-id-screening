import React from 'react';
import { Linking, Platform, StyleSheet, View } from 'react-native';

import { colors, spacing } from '../../theme';
import { Button } from '../Button';
import { Text } from '../Text';

export type PermissionPhase = 'checking' | 'undetermined' | 'denied' | 'blocked' | 'unavailable';

interface CameraPermissionGateProps {
  phase: PermissionPhase;
  /** Requests the OS permission again (only meaningful when it can be asked). */
  onRequest: () => void;
  /** Leaves the camera step. */
  onCancel: () => void;
  /** Extra detail for the `unavailable` phase. */
  errorMessage?: string | null;
}

const COPY: Record<
  Exclude<PermissionPhase, 'checking'>,
  { title: string; body: string }
> = {
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
};

/**
 * Full-screen state shown whenever a real preview cannot be rendered:
 * permission still to be asked, refused, blocked in settings, or no camera.
 * The user always has a next action — never a blank camera screen.
 */
export function CameraPermissionGate({
  phase,
  onRequest,
  onCancel,
  errorMessage,
}: CameraPermissionGateProps) {
  if (phase === 'checking') {
    return (
      <View style={styles.root} accessibilityLiveRegion="polite">
        <Text variant="body" tone="inverseMuted" center>
          Preparing the camera…
        </Text>
      </View>
    );
  }

  const copy = COPY[phase];
  const canRequest = phase === 'undetermined' || phase === 'denied';

  return (
    <View style={styles.root}>
      <View style={styles.body}>
        <Text style={styles.glyph} accessibilityElementsHidden>
          📷
        </Text>
        <Text variant="title" tone="inverse" center>
          {copy.title}
        </Text>
        <Text variant="body" tone="inverseMuted" center>
          {copy.body}
        </Text>
        {errorMessage && phase === 'unavailable' ? (
          <Text variant="caption" tone="inverseMuted" center>
            {errorMessage}
          </Text>
        ) : null}
      </View>

      <View style={styles.actions}>
        {canRequest ? (
          <Button
            label={phase === 'denied' ? 'Try again' : 'Allow camera access'}
            onPress={onRequest}
            accessibilityHint="Asks the operating system for camera permission"
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

        <Button label="Go back" variant="ghost" onPress={onCancel} />
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
  actions: {
    gap: spacing.sm,
  },
});
