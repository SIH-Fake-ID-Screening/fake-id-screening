import React from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Image } from 'expo-image';

import { Badge, Button, Card, Screen, Text } from '../components';
import { CAPTURE_SLOTS } from '../constants/captureSlots';
import { useCaptures } from '../context/CaptureContext';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Final confirmation before anything is uploaded.
 *
 * Lists the three slots with their state, a thumbnail of the captured image
 * and per-slot retake actions. Images come straight from `CaptureContext`
 * (local cache URIs produced by the camera step) — nothing is uploaded here.
 */
export function ReviewScreen({ navigation }: RootStackScreenProps<'Review'>) {
  const { captures, isComplete, completedCount } = useCaptures();

  return (
    <Screen
      footer={
        <>
          <Button
            label="Start Verification"
            icon="🔍"
            disabled={!isComplete}
            onPress={() => navigation.navigate('Processing')}
            accessibilityHint="Uploads the three photos for screening"
          />
          <Text variant="caption" tone="tertiary" center>
            {isComplete
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
