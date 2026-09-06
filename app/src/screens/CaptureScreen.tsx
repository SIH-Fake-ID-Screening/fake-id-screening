import React from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Button, Card, Screen, StepIndicator, Text } from '../components';
import { CAPTURE_ORDER, CAPTURE_SLOT_MAP } from '../constants/captureSlots';
import { useCaptures } from '../context/CaptureContext';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Capture step shell.
 *
 * MILESTONE 1: layout, framing-guide placeholder and flow navigation only.
 * The live camera preview and shutter are added in Milestone 2, which will
 * replace the placeholder block below.
 */
export function CaptureScreen({ navigation, route }: RootStackScreenProps<'Capture'>) {
  const { slot } = route.params;
  const meta = CAPTURE_SLOT_MAP[slot];
  const stepIndex = CAPTURE_ORDER.indexOf(slot);
  const { setCapture } = useCaptures();

  const goToNextStep = () => {
    const next = CAPTURE_ORDER[stepIndex + 1];
    if (next) {
      navigation.replace('Capture', { slot: next });
    } else {
      navigation.replace('Review');
    }
  };

  // Temporary stand-in until the camera lands in Milestone 2. It records a
  // placeholder entry so the flow (and Review screen) can be navigated now.
  const handlePlaceholderCapture = () => {
    setCapture(slot, {
      uri: '',
      width: 0,
      height: 0,
      fileName: `${meta.field}.jpg`,
      mimeType: 'image/jpeg',
      capturedAt: Date.now(),
    });
    goToNextStep();
  };

  return (
    <Screen
      scroll={false}
      footer={
        <Button
          label="Continue"
          onPress={handlePlaceholderCapture}
          accessibilityHint={`Continues past the ${meta.label} step`}
        />
      }
    >
      <StatusBar style="dark" />

      <StepIndicator current={stepIndex + 1} total={CAPTURE_ORDER.length} label={meta.label} />

      <View style={styles.intro}>
        <Text variant="title">{meta.title}</Text>
        <Text variant="body" tone="secondary">
          {meta.description}
        </Text>
      </View>

      {/* Framing-guide preview area (camera preview arrives in Milestone 2) */}
      <View style={styles.previewArea}>
        <View style={[styles.guide, meta.guide === 'face' ? styles.guideFace : styles.guideCard]}>
          <Text variant="caption" tone="tertiary" center>
            Camera preview
          </Text>
          <Text variant="caption" tone="tertiary" center>
            (coming in the next milestone)
          </Text>
        </View>
      </View>

      <Card variant="plain">
        <Text variant="label" tone="tertiary">
          Tips
        </Text>
        <View style={styles.tips}>
          {meta.tips.map((tip) => (
            <View key={tip} style={styles.tipRow}>
              <View style={styles.tipDot} />
              <Text variant="caption" tone="secondary" style={styles.tipText}>
                {tip}
              </Text>
            </View>
          ))}
        </View>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  intro: {
    gap: spacing.xs,
    marginTop: spacing.xl,
    marginBottom: spacing.lg,
  },
  previewArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  guide: {
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: colors.borderStrong,
    backgroundColor: colors.surfaceMuted,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    padding: spacing.lg,
  },
  guideCard: {
    width: '100%',
    aspectRatio: 1.58, // ID-1 card ratio
    borderRadius: radii.lg,
  },
  guideFace: {
    width: '72%',
    aspectRatio: 0.78,
    borderRadius: radii.pill,
  },
  tips: {
    gap: spacing.sm,
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
    backgroundColor: colors.textTertiary,
    marginTop: 7,
  },
  tipText: {
    flex: 1,
  },
});
