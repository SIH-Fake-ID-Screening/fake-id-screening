import React from 'react';
import { StyleSheet, View } from 'react-native';

import { colors, spacing } from '../theme';
import { Text } from './Text';

interface InfoRowProps {
  label: string;
  value?: string | null;
  /** Text shown when `value` is null/empty — the backend often omits fields. */
  fallback?: string;
  emphasis?: boolean;
  divider?: boolean;
}

/**
 * Label/value row used on the result screen. Missing values are rendered as an
 * explicit placeholder instead of an empty gap, because several student fields
 * are optional in the backend schema.
 */
export function InfoRow({
  label,
  value,
  fallback = 'Not provided',
  emphasis = false,
  divider = true,
}: InfoRowProps) {
  const hasValue = typeof value === 'string' && value.trim().length > 0;

  return (
    <View style={[styles.row, divider && styles.divider]}>
      <Text variant="caption" tone="secondary" style={styles.label}>
        {label}
      </Text>
      <Text
        variant={emphasis ? 'bodyStrong' : 'body'}
        tone={hasValue ? 'primary' : 'tertiary'}
        style={styles.value}
      >
        {hasValue ? value!.trim() : fallback}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: spacing.lg,
    paddingVertical: spacing.md,
  },
  divider: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  label: {
    flexShrink: 0,
    maxWidth: '42%',
  },
  value: {
    flex: 1,
    textAlign: 'right',
  },
});
