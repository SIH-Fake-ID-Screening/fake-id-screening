import React, { useCallback, useState } from 'react';
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
 * (local cache URIs produced by the camera step) — the same URI is displayed
 * and uploaded, so nothing is copied or duplicated.
 *
 * Submitting starts the real `POST /api/v1/screen` upload. The request is
 * owned by `ScreeningContext`, so moving to the Processing screen does not
 * interrupt it, and a failed attempt can be retried from here with the same
 * images — no recapture needed.
 */
export function ReviewScreen({ navigation }: RootStackScreenProps<'Review'>) {
  const { captures, isComplete, completedCount, nextIncompleteSlot } = useCaptures();
  const { submit, isSubmitting, error, isConfigured, phase, wasCancelled } = useScreening();

  /** Explains a blocked submit tap (e.g. a photo is still missing). */
  const [blockedReason, setBlockedReason] = useState<string | null>(null);

  const hasFailed = phase === 'failed' && error !== null;
  const dangerTone = toneStyles('danger');
  const warningTone = toneStyles('warning');
  const canSubmit = isComplete && isConfigured && !isSubmitting;

  const startVerification = useCallback(() => {
    // Duplicate-submit protection is layered: the button is disabled while a
    // request is in flight, and `ScreeningContext.submit` also refuses
    // re-entry synchronously.
    if (isSubmitting) return;

    if (!isConfigured) {
      setBlockedReason(
        'No screening server address is configured, so the photos cannot be submitted. ' +
          'Set EXPO_PUBLIC_API_BASE_URL and restart the app.',
      );
      return;
    }

    if (!isComplete) {
      const missing = CAPTURE_SLOTS.filter((meta) => captures[meta.slot] === null)
        .map((meta) => meta.label.toLowerCase())
        .join(', ');

      setBlockedReason(
        `All three photos are needed before screening can start. Still missing: ${missing}.`,
      );
      return;
    }

    setBlockedReason(null);

    // Fire the upload, then show the shared processing screen. The promise is
    // intentionally not awaited here: its outcome is read from context by the
    // Processing screen, which is what advances to Result.
    void submit();
    navigation.navigate('Processing');
  }, [captures, isComplete, isConfigured, isSubmitting, navigation, submit]);

  const goToCapture = useCallback(
    (slot: (typeof CAPTURE_SLOTS)[number]['slot']) => {
      setBlockedReason(null);
      // `returnTo` brings the user straight back here after the retake.
      navigation.navigate('Capture', { slot, returnTo: 'Review' });
    },
    [navigation],
  );

  const submitLabel = isSubmitting
    ? 'Submitting…'
    : hasFailed
      ? 'Try verification again'
      : 'Start Verification';

  const footerNote = !isConfigured
    ? 'No screening server is configured, so submission is disabled.'
    : isSubmitting
      ? 'Uploading your photos — keep the app open.'
      : isComplete
        ? 'Your photos are sent over a secure connection for screening.'
        : `${completedCount} of ${CAPTURE_SLOTS.length} photos captured.`;

  return (
    <Screen
      footer={
        <>
          <Button
            label={submitLabel}
            icon={hasFailed ? '↻' : '🔍'}
            disabled={!canSubmit}
            loading={isSubmitting}
            onPress={startVerification}
            accessibilityHint={
              canSubmit
                ? 'Uploads the three photos for screening'
                : 'Unavailable until all three photos are captured'
            }
          />
          <Text variant="caption" tone="tertiary" center accessibilityLiveRegion="polite">
            {footerNote}
          </Text>
        </>
      }
    >
      <StatusBar style="dark" />

      <View style={styles.intro}>
        <Text variant="title" accessibilityRole="header">
          Review your submission
        </Text>
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

      {/* A user-cancelled attempt is reported calmly, not as an error. */}
      {!hasFailed && wasCancelled ? (
        <View
          style={[
            styles.notice,
            { backgroundColor: warningTone.bg, borderColor: warningTone.border },
          ]}
          accessibilityLiveRegion="polite"
        >
          <Text variant="label" style={{ color: warningTone.fg }}>
            Verification cancelled
          </Text>
          <Text variant="caption" style={{ color: warningTone.fg }}>
            Nothing was screened. Your photos are still here — submit again when you're ready.
          </Text>
        </View>
      ) : null}

      {/* Why a submit tap did not proceed. */}
      {blockedReason ? (
        <View
          style={[
            styles.notice,
            { backgroundColor: warningTone.bg, borderColor: warningTone.border },
          ]}
          accessibilityRole="alert"
        >
          <Text variant="label" style={{ color: warningTone.fg }}>
            Cannot submit yet
          </Text>
          <Text variant="caption" style={{ color: warningTone.fg }}>
            {blockedReason}
          </Text>
          {nextIncompleteSlot ? (
            <Button
              label="Capture the missing photo"
              variant="secondary"
              size="md"
              onPress={() => goToCapture(nextIncompleteSlot)}
            />
          ) : null}
        </View>
      ) : null}

      <View style={styles.list}>
        {CAPTURE_SLOTS.map((meta) => {
          const capture = captures[meta.slot];
          // A stored capture with an empty URI would be unusable, so treat it
          // as missing rather than showing a broken thumbnail.
          const captured =
            capture !== null && typeof capture.uri === 'string' && capture.uri.trim().length > 0;

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
                onPress={() => goToCapture(meta.slot)}
                accessibilityHint={
                  captured
                    ? `Reopens the camera to replace the ${meta.label.toLowerCase()} photo`
                    : `Opens the camera to take the ${meta.label.toLowerCase()} photo`
                }
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
