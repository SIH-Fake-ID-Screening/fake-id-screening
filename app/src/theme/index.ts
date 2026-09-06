import { Platform, TextStyle } from 'react-native';

export { colors, palette, toneStyles } from './colors';
export type { SemanticTone } from './colors';

/** 4pt-based spacing scale. */
export const spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 40,
  giant: 56,
} as const;

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 28,
  pill: 999,
} as const;

const fontFamily = Platform.select({
  android: 'sans-serif',
  ios: 'System',
  default: 'System',
});

const fontFamilyMedium = Platform.select({
  android: 'sans-serif-medium',
  ios: 'System',
  default: 'System',
});

/**
 * Typography scale. On Android we swap the family rather than relying on
 * numeric font weights, which render inconsistently below API 28.
 */
export const typography = {
  display: {
    fontFamily: fontFamilyMedium,
    fontSize: 32,
    lineHeight: 38,
    fontWeight: '700',
    letterSpacing: -0.6,
  } as TextStyle,
  title: {
    fontFamily: fontFamilyMedium,
    fontSize: 24,
    lineHeight: 30,
    fontWeight: '700',
    letterSpacing: -0.4,
  } as TextStyle,
  heading: {
    fontFamily: fontFamilyMedium,
    fontSize: 18,
    lineHeight: 24,
    fontWeight: '600',
    letterSpacing: -0.2,
  } as TextStyle,
  subheading: {
    fontFamily: fontFamilyMedium,
    fontSize: 16,
    lineHeight: 22,
    fontWeight: '600',
  } as TextStyle,
  body: {
    fontFamily,
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '400',
  } as TextStyle,
  bodyStrong: {
    fontFamily: fontFamilyMedium,
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '600',
  } as TextStyle,
  caption: {
    fontFamily,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '400',
  } as TextStyle,
  label: {
    fontFamily: fontFamilyMedium,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  } as TextStyle,
  mono: {
    fontFamily: Platform.select({ android: 'monospace', default: 'Menlo' }),
    fontSize: 14,
    lineHeight: 20,
  } as TextStyle,
} as const;

/** Cross-platform elevation presets. */
export const shadows = {
  none: {},
  card: Platform.select({
    android: { elevation: 2 },
    default: {
      shadowColor: '#0F172A',
      shadowOpacity: 0.06,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
    },
  }) as object,
  raised: Platform.select({
    android: { elevation: 6 },
    default: {
      shadowColor: '#0F172A',
      shadowOpacity: 0.12,
      shadowRadius: 20,
      shadowOffset: { width: 0, height: 8 },
    },
  }) as object,
} as const;

/** Minimum touch target per Android accessibility guidance. */
export const HIT_SLOP = { top: 8, bottom: 8, left: 8, right: 8 } as const;
export const MIN_TOUCH_SIZE = 48;
