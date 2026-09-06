import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from 'react-native';

import { MIN_TOUCH_SIZE, colors, radii, shadows, spacing, typography } from '../theme';
import { Text } from './Text';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'md' | 'lg';

interface ButtonProps {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  /** Optional leading glyph (kept as text to avoid an icon dependency). */
  icon?: string;
  fullWidth?: boolean;
  style?: StyleProp<ViewStyle>;
  accessibilityHint?: string;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  size = 'lg',
  disabled = false,
  loading = false,
  icon,
  fullWidth = true,
  style,
  accessibilityHint,
}: ButtonProps) {
  const isInteractive = !disabled && !loading;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !isInteractive, busy: loading }}
      onPress={isInteractive ? onPress : undefined}
      disabled={!isInteractive}
      android_ripple={
        variant === 'ghost' ? { color: colors.border } : { color: 'rgba(255,255,255,0.22)' }
      }
      style={({ pressed }) => [
        styles.base,
        size === 'md' ? styles.sizeMd : styles.sizeLg,
        VARIANTS[variant].container,
        fullWidth && styles.fullWidth,
        pressed && isInteractive && VARIANTS[variant].pressed,
        !isInteractive && styles.disabled,
        style,
      ]}
    >
      <View style={styles.inner}>
        {loading ? (
          <ActivityIndicator size="small" color={VARIANTS[variant].labelColor} />
        ) : (
          <>
            {icon ? (
              <Text style={[styles.icon, { color: VARIANTS[variant].labelColor }]}>{icon}</Text>
            ) : null}
            <Text
              style={[
                size === 'md' ? typography.bodyStrong : typography.subheading,
                { color: VARIANTS[variant].labelColor },
              ]}
              numberOfLines={1}
            >
              {label}
            </Text>
          </>
        )}
      </View>
    </Pressable>
  );
}

const VARIANTS: Record<
  Variant,
  { container: ViewStyle; pressed: ViewStyle; labelColor: string }
> = {
  primary: {
    container: { backgroundColor: colors.primary, ...shadows.card },
    pressed: { backgroundColor: colors.primaryPressed },
    labelColor: colors.textInverse,
  },
  secondary: {
    container: {
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.borderStrong,
    },
    pressed: { backgroundColor: colors.surfaceMuted },
    labelColor: colors.textPrimary,
  },
  ghost: {
    container: { backgroundColor: 'transparent' },
    pressed: { backgroundColor: colors.surfaceMuted },
    labelColor: colors.primary,
  },
  danger: {
    container: { backgroundColor: colors.danger, ...shadows.card },
    pressed: { backgroundColor: '#B91C1C' },
    labelColor: colors.textInverse,
  },
};

const styles = StyleSheet.create({
  base: {
    borderRadius: radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  sizeLg: {
    minHeight: 54,
    paddingHorizontal: spacing.xxl,
  },
  sizeMd: {
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: spacing.lg,
  },
  fullWidth: {
    alignSelf: 'stretch',
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  icon: {
    fontSize: 16,
  },
  disabled: {
    opacity: 0.45,
  },
});
