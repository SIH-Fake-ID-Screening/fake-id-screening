import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Image } from 'expo-image';

import { colors, radii, spacing } from '../../theme';
import { Button } from '../Button';
import { Text } from '../Text';

interface ShotPreviewProps {
  uri: string;
  title: string;
  /** Guidance for judging the shot. */
  checklist: readonly string[];
  onRetake: () => void;
  onConfirm: () => void;
  confirmLabel: string;
}

/**
 * Shown immediately after the shutter fires so the user can judge quality and
 * retake before the image is committed to the flow.
 */
export function ShotPreview({
  uri,
  title,
  checklist,
  onRetake,
  onConfirm,
  confirmLabel,
}: ShotPreviewProps) {
  return (
    <View style={styles.root}>
      <View style={styles.imageArea}>
        <Image
          source={{ uri }}
          style={styles.image}
          contentFit="contain"
          transition={0}
          accessibilityLabel={`Captured photo: ${title}`}
        />
      </View>

      <View style={styles.panel}>
        <Text variant="subheading" tone="inverse">
          {title}
        </Text>

        <View style={styles.checklist}>
          {checklist.map((item) => (
            <View key={item} style={styles.checkRow}>
              <Text variant="caption" tone="inverseMuted">
                ✓
              </Text>
              <Text variant="caption" tone="inverseMuted" style={styles.checkText}>
                {item}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.actions}>
          <Button
            label={confirmLabel}
            onPress={onConfirm}
            accessibilityHint="Keeps this photo and continues"
          />
          <Button
            label="Retake photo"
            variant="secondary"
            onPress={onRetake}
            accessibilityHint="Discards this photo and reopens the camera"
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.surfaceDark,
  },
  imageArea: {
    flex: 1,
    padding: spacing.lg,
  },
  image: {
    flex: 1,
    borderRadius: radii.lg,
    backgroundColor: '#000000',
  },
  panel: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    paddingBottom: spacing.lg,
    gap: spacing.md,
  },
  checklist: {
    gap: spacing.xs,
  },
  checkRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'flex-start',
  },
  checkText: {
    flex: 1,
  },
  actions: {
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
});
