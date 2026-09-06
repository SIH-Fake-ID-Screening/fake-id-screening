import React from 'react';
import { StyleSheet, View } from 'react-native';

import { colors, radii, spacing } from '../theme';
import { Text } from './Text';

interface StepIndicatorProps {
  /** 1-based index of the active step. */
  current: number;
  total: number;
  label?: string;
}

/**
 * Slim progress bar for the capture flow. A bar rather than numbered dots so
 * it stays legible at small widths and reads well in a demo.
 */
export function StepIndicator({ current, total, label }: StepIndicatorProps) {
  const safeTotal = Math.max(total, 1);
  const safeCurrent = Math.min(Math.max(current, 1), safeTotal);

  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={`Step ${safeCurrent} of ${safeTotal}${label ? `: ${label}` : ''}`}
      style={styles.wrapper}
    >
      <View style={styles.row}>
        <Text variant="label" tone="tertiary">
          Step {safeCurrent} of {safeTotal}
        </Text>
        {label ? (
          <Text variant="caption" tone="secondary" numberOfLines={1} style={styles.label}>
            {label}
          </Text>
        ) : null}
      </View>

      <View style={styles.track}>
        {Array.from({ length: safeTotal }).map((_, index) => (
          <View
            key={index}
            style={[styles.segment, index < safeCurrent ? styles.segmentActive : null]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  label: {
    flexShrink: 1,
    textAlign: 'right',
  },
  track: {
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  segment: {
    flex: 1,
    height: 5,
    borderRadius: radii.pill,
    backgroundColor: colors.border,
  },
  segmentActive: {
    backgroundColor: colors.primary,
  },
});
