import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import { SemanticTone, radii, spacing, toneStyles, typography } from '../theme';
import { Text } from './Text';

interface BadgeProps {
  label: string;
  tone?: SemanticTone;
  icon?: string;
  style?: StyleProp<ViewStyle>;
}

/** Compact status pill used for statuses and trust markers. */
export function Badge({ label, tone = 'neutral', icon, style }: BadgeProps) {
  const t = toneStyles(tone);

  return (
    <View style={[styles.badge, { backgroundColor: t.bg, borderColor: t.border }, style]}>
      {icon ? <Text style={[styles.icon, { color: t.fg }]}>{icon}</Text> : null}
      <Text style={[typography.caption, styles.label, { color: t.fg }]} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: radii.pill,
    borderWidth: 1,
  },
  label: {
    fontWeight: '600',
  },
  icon: {
    fontSize: 12,
  },
});
