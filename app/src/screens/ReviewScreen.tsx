import React, { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Image } from 'expo-image';

import { Badge, Button, Card, Screen, Text } from '../components';
import { CAPTURE_SLOTS } from '../constants/captureSlots';
import { useCaptures } from '../context/CaptureContext';
import { useScreening } from '../context/ScreeningContext';
import { colors, radii, spacing, toneStyles } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Final confirmation before anything is uploaded.
 *
 * Lists the three slots with their state, a thumbnail of the captured image
 * and per-slot retake actions. Images come straight from `CaptureContext`
 * (local cache URIs produced by the camera step).
 *
 * Submitting starts the real `POST /api/v1/screen` upload. The request is
 * owned by `ScreeningContext`, so moving to the Processing screen does not
 * interrupt it, and a failed attempt can be retried from here with the same
 * images — no recapture needed.
 */
export function ReviewScreen({ navigation }: RootStackScreenProps<'Review'>) {
  const { captures, isComplete, completedCount } = useCaptures();
  const { submit, isSubmitting, error, isConfigured, phase } = useScreening();

  const hasFailed = phase === 'failed' && error !== null;
  const dangerTone = toneStyles('danger');

  const startVerification = useCallback(() => {
    if (isSubmitting || !isComplete) return;

    // Fire the upload, then show the shared processing screen. The promise is
    // intentionally not awaited here: its outcome is read from context by the
    // Processing screen, which is what advances to Result.
    void submit();
    navigation.navigate('Processing');
  }, [isComplete, isSubmitting, navigation, submit]);

  const submitLabel = isSubmitting
    ? 'Submitting…'
    : hasFailed
      ? 'Try verification again'
      : 'Start Verification';

  return (
    <Screen
      footer={
        <>
          <Button
            label={submitLabel}
            icon={hasFailed ? '↻' : '🔍'}
            disabled={!isComplete || !isConfigured}
            loading={isSubmitting}
            onPress={startVerification}
            accessibilityHint="Uploads the three photos for screening"
          />
          <Text variant="caption" tone="tertiary" center>
            {!isConfigured
              ? 'No screening server is configured, so submission is disabled.'
              : isSubmitting
                ? 'Uploading your photos — keep the app open.'
                : isComplete
                  ? 'Your photos are sent over a secure connection for screening.'
                  : `${completedCount} of ${CAPTURE_SLOTS.length} photos captured.`}
          </Text>
        </>
      }
    >
      <StatusBar style="dark" />

      <View style={styles.intro}>
        <Text variant="title">Review your submission</Text>
        <Text variant="body" tone="secondary">
          Check each photo is clear and readable. You can retake any of them before submitting.
        </Text>
      </View>

      {/* Misconfiguration is shown up front so the disabled button is explained. */}
      {!isConfigured ? (
        <View
          style={[
            styles.notice,
            { backgroundColor: dangerTone.bg, borderColor: dangerTone.border },
          ]}
        >
          <Text variant="label" style={{ color: dangerTone.fg }}>
            Screening server not configured
          </Text>
          <Text variant="caption" style={{ color: dangerTone.fg }}>
            Set EXPO_PUBLIC_API_BASE_URL to the address of the screening backend and restart the
            app. See app/README.md for local setup.
          </Text>
        </View>
      ) : null}

      {/* Last failure, kept visible so the user can retry deliberately. */}
      {hasFailed && error ? (
        <View
          style={[
            styles.notice,
            { backgroundColor: dangerTone.bg, borderColor: dangerTone.border },
          ]}
          accessibilityRole="alert"
        >
          <Text variant="label" style={{ color: dangerTone.fg }}>
            Verification could not be completed
          </Text>
          <Text variant="caption" style={{ color: dangerTone.fg }}>
            {error.message}
          </Text>
          <Text variant="caption" style={{ color: dangerTone.fg }}>
            Your photos have been kept — you can submit again without retaking them.
          </Text>
        </View>
      ) : null}

      <View style={styles.list}>
        {CAPTURE_SLOTS.map((meta) => {
          const capture = captures[meta.slot];
          const captured = capture !== null && capture.uri.length > 0;

          return (
            <Card key={meta.slot} style={styles.item}>
              <View style={styles.itemHeader}>
                <View style={styles.itemHeading}>
                  <Text variant="subheading">{meta.title}</Text>
                  <Text variant="caption" tone="secondary">
                    {meta.description}
                  </Text>
                </View>
                <Badge
                  label={captured ? 'Captured' : 'Missing'}
                  tone={captured ? 'success' : 'warning'}
                  icon={captured ? '✓' : '!'}
                />
              </View>

              <View
                style={[
                  styles.thumb,
                  meta.guide === 'face' ? styles.thumbFace : styles.thumbCard,
                ]}
              >
                {captured && capture ? (
                  <Image
                    source={{ uri: capture.uri }}
                    style={styles.thumbImage}
                    contentFit="cover"
                    transition={0}
                    accessibilityLabel={`Captured photo of the ${meta.label}`}
                  />
                ) : (
                  <Text variant="caption" tone="tertiary">
                    Not captured yet
                  </Text>
                )}
              </View>

              <Button
                label={captured ? 'Retake this photo' : 'Capture now'}
                variant="secondary"
                size="md"
                disabled={isSubmitting}
                onPress={() => navigation.navigate('Capture', { slot: meta.slot })}
              />
            </Card>
          );
        })}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  intro: {
    gap: spacing.xs,
    marginBottom: spacing.xl,
  },
  notice: {
    borderRadius: radii.lg,
    borderWidth: 1,
    padding: spacing.lg,
    gap: spacing.xs,
    marginBottom: spacing.lg,
  },
  list: {
    gap: spacing.lg,
  },
  item: {
    gap: spacing.md,
  },
  itemHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  itemHeading: {
    flex: 1,
    gap: spacing.xxs,
  },
  thumb: {
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  thumbCard: {
    width: '100%',
    aspectRatio: 1.58,
  },
  thumbFace: {
    width: '100%',
    aspectRatio: 1.2,
  },
  thumbImage: {
    width: '100%',
    height: '100%',
  },
});
