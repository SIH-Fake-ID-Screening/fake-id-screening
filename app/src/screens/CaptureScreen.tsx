import React, { useCallback, useEffect, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, StepIndicator, Text } from '../components';
import { CameraCaptureView, ShotPreview } from '../components/camera';
import type { CameraShot } from '../components/camera';
import { CAPTURE_ORDER, CAPTURE_SLOT_MAP } from '../constants/captureSlots';
import { useCaptures } from '../context/CaptureContext';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';
import type { CaptureSlot } from '../types/screening';

/**
 * Capture step: a real device camera preview, framing guide and shutter,
 * followed by an in-place confirm/retake preview.
 *
 * The image URI produced by `expo-camera` (app cache directory) is stored in
 * `CaptureContext` — memory only, never written to persistent storage by the
 * app — and the flow continues to the next slot or back to Review.
 */
export function CaptureScreen({ navigation, route }: RootStackScreenProps<'Capture'>) {
  const { slot, returnTo } = route.params ?? {};
  const { setCapture } = useCaptures();

  /** The freshly taken shot awaiting confirmation, if any. */
  const [pendingShot, setPendingShot] = useState<CameraShot | null>(null);
  /** Blocks a second confirm tap while navigation is settling. */
  const confirming = useRef(false);

  // Reopen the camera when the slot changes (e.g. front → back) and drop any
  // shot that was still awaiting confirmation for the previous slot.
  useEffect(() => {
    setPendingShot(null);
    confirming.current = false;
  }, [slot]);

  const isKnownSlot = typeof slot === 'string' && slot in CAPTURE_SLOT_MAP;

  const goHome = useCallback(() => {
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  }, [navigation]);

  const handleCancel = useCallback(() => {
    // Discard the unconfirmed shot so leaving never commits a half-reviewed
    // photo into the capture bundle.
    setPendingShot(null);

    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      goHome();
    }
  }, [goHome, navigation]);

  // A malformed/unknown route param must not crash the screen: `meta` would be
  // undefined and every read below would throw. Recover to Home instead.
  if (!isKnownSlot) {
    return (
      <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
        <StatusBar style="light" />
        <View style={styles.fallback} accessibilityRole="alert">
          <Text variant="title" tone="inverse" center>
            Capture step unavailable
          </Text>
          <Text variant="body" tone="inverseMuted" center>
            This capture step could not be opened. Please start the verification again.
          </Text>
          <Button label="Back to start" onPress={goHome} />
        </View>
      </SafeAreaView>
    );
  }

  const validSlot = slot as CaptureSlot;
  const meta = CAPTURE_SLOT_MAP[validSlot];
  const stepIndex = CAPTURE_ORDER.indexOf(validSlot);
  const isLastStep = stepIndex === CAPTURE_ORDER.length - 1;

  const handleConfirm = () => {
    if (!pendingShot || confirming.current) return;

    // Defend against an empty URI slipping through: without it the multipart
    // part would be unusable and the backend would reject the submission.
    if (typeof pendingShot.uri !== 'string' || pendingShot.uri.trim().length === 0) {
      setPendingShot(null);
      return;
    }

    confirming.current = true;

    const isPng = pendingShot.format === 'png';

    // Replaces whatever was in this exact slot, so a retake can never land on
    // a different photo.
    setCapture(validSlot, {
      uri: pendingShot.uri,
      width: pendingShot.width,
      height: pendingShot.height,
      fileName: `${meta.field}.${isPng ? 'png' : 'jpg'}`,
      mimeType: isPng ? 'image/png' : 'image/jpeg',
      facing: pendingShot.facing,
      capturedAt: Date.now(),
    });

    setPendingShot(null);

    // Retakes launched from Review return there directly instead of walking
    // the remaining steps again. The destination comes from the route param,
    // not from inspecting the stack.
    if (returnTo === 'Review') {
      navigation.navigate('Review');
      return;
    }

    const next = CAPTURE_ORDER[stepIndex + 1];
    if (next) {
      navigation.replace('Capture', { slot: next });
    } else {
      navigation.replace('Review');
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <StatusBar style="light" />

      <View style={styles.header}>
        <StepIndicator current={stepIndex + 1} total={CAPTURE_ORDER.length} label={meta.label} />
        <View style={styles.intro}>
          <Text variant="subheading" tone="inverse">
            {meta.title}
          </Text>
          <Text variant="caption" tone="inverseMuted">
            {pendingShot ? 'Check the photo is sharp and complete.' : meta.description}
          </Text>
        </View>
      </View>

      {pendingShot ? (
        <ShotPreview
          uri={pendingShot.uri}
          title={meta.title}
          checklist={meta.tips}
          confirmLabel={
            returnTo === 'Review'
              ? 'Use photo & back to review'
              : isLastStep
                ? 'Use photo & review'
                : 'Use photo & continue'
          }
          onRetake={() => {
            confirming.current = false;
            setPendingShot(null);
          }}
          onConfirm={handleConfirm}
        />
      ) : (
        <CameraCaptureView
          facing={meta.facing}
          guide={meta.guide}
          hint={meta.tips[0]}
          captureLabel={`Capture ${meta.label}`}
          allowFlip={meta.guide === 'face'}
          onCaptured={setPendingShot}
          onCancel={handleCancel}
        />
      )}

      {pendingShot ? null : (
        <Card variant="plain" style={styles.tipsCard}>
          <Text variant="label" tone="inverseMuted">
            Tips
          </Text>
          <View style={styles.tips}>
            {meta.tips.map((tip) => (
              <View key={tip} style={styles.tipRow}>
                <View style={styles.tipDot} />
                <Text variant="caption" tone="inverseMuted" style={styles.tipText}>
                  {tip}
                </Text>
              </View>
            ))}
          </View>
        </Card>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.surfaceDark,
  },
  header: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
    gap: spacing.md,
  },
  intro: {
    gap: spacing.xxs,
  },
  fallback: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.xxl,
    gap: spacing.lg,
  },
  tipsCard: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.md,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderColor: 'rgba(255,255,255,0.16)',
    borderRadius: radii.lg,
  },
  tips: {
    gap: spacing.xs,
    marginTop: spacing.sm,
  },
  tipRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  tipDot: {
    width: 5,
    height: 5,
    borderRadius: radii.pill,
    backgroundColor: colors.textInverseMuted,
    marginTop: 7,
  },
  tipText: {
    flex: 1,
  },
});
