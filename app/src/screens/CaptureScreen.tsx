import React, { useCallback, useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Card, StepIndicator, Text } from '../components';
import { CameraCaptureView, ShotPreview } from '../components/camera';
import type { CameraShot } from '../components/camera';
import { CAPTURE_ORDER, CAPTURE_SLOT_MAP } from '../constants/captureSlots';
import { useCaptures } from '../context/CaptureContext';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Capture step: a real device camera preview, framing guide and shutter,
 * followed by an in-place confirm/retake preview.
 *
 * MILESTONE 2: the placeholder preview block is replaced by `expo-camera`.
 * The image URI is stored in `CaptureContext` (memory only) and the flow
 * continues to the next slot or to Review, exactly as before.
 */
export function CaptureScreen({ navigation, route }: RootStackScreenProps<'Capture'>) {
  const { slot } = route.params;
  const meta = CAPTURE_SLOT_MAP[slot];
  const stepIndex = CAPTURE_ORDER.indexOf(slot);
  const isLastStep = stepIndex === CAPTURE_ORDER.length - 1;
  const { setCapture } = useCaptures();

  /** The freshly taken shot awaiting confirmation, if any. */
  const [pendingShot, setPendingShot] = useState<CameraShot | null>(null);

  // Reopen the camera when the slot changes (e.g. front → back).
  useEffect(() => {
    setPendingShot(null);
  }, [slot]);

  const goToNextStep = useCallback(() => {
    const next = CAPTURE_ORDER[stepIndex + 1];
    if (next) {
      navigation.replace('Capture', { slot: next });
    } else {
      navigation.replace('Review');
    }
  }, [navigation, stepIndex]);

  const handleCancel = useCallback(() => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.replace('Home');
    }
  }, [navigation]);

  const handleConfirm = useCallback(() => {
    if (!pendingShot) {
      return;
    }

    setCapture(slot, {
      uri: pendingShot.uri,
      width: pendingShot.width,
      height: pendingShot.height,
      fileName: `${meta.field}.${pendingShot.format === 'png' ? 'png' : 'jpg'}`,
      mimeType: pendingShot.format === 'png' ? 'image/png' : 'image/jpeg',
      facing: pendingShot.facing,
      capturedAt: Date.now(),
    });

    setPendingShot(null);

    // If the user arrived here from Review to retake one photo, send them
    // straight back instead of walking the remaining steps again.
    const cameFromReview = navigation
      .getState()
      ?.routes.some((r) => r.name === 'Review');

    if (cameFromReview) {
      navigation.navigate('Review');
      return;
    }

    goToNextStep();
  }, [goToNextStep, meta.field, navigation, pendingShot, setCapture, slot]);

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
          confirmLabel={isLastStep ? 'Use photo & review' : 'Use photo & continue'}
          onRetake={() => setPendingShot(null)}
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
