import React from 'react';
import { StyleProp, Text as RNText, TextProps as RNTextProps, TextStyle } from 'react-native';

import { colors, typography } from '../theme';

type Variant = keyof typeof typography;
type Tone = 'primary' | 'secondary' | 'tertiary' | 'inverse' | 'inverseMuted' | 'brand' | 'success' | 'warning' | 'danger';

const TONE_COLORS: Record<Tone, string> = {
  primary: colors.textPrimary,
  secondary: colors.textSecondary,
  tertiary: colors.textTertiary,
  inverse: colors.textInverse,
  inverseMuted: colors.textInverseMuted,
  brand: colors.primary,
  success: colors.success,
  warning: colors.warning,
  danger: colors.danger,
};

export interface TextProps extends RNTextProps {
  variant?: Variant;
  tone?: Tone;
  center?: boolean;
  style?: StyleProp<TextStyle>;
}

/**
 * Typed text primitive. Every string in the app goes through this so the
 * type scale and colour tones stay consistent.
 */
export function Text({
  variant = 'body',
  tone = 'primary',
  center = false,
  style,
  ...rest
}: TextProps) {
  return (
    <RNText
      style={[
        typography[variant],
        { color: TONE_COLORS[tone] },
        center && { textAlign: 'center' },
        style,
      ]}
      {...rest}
    />
  );
}
