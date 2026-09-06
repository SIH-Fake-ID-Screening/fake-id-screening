/**
 * Colour tokens for the design system.
 *
 * The palette is intentionally restrained: a deep navy/indigo base for a
 * security-product feel, one accent used for primary actions, and a small
 * set of semantic colours for verification outcomes.
 */

export const palette = {
  // Neutrals (slate ramp)
  white: '#FFFFFF',
  slate50: '#F8FAFC',
  slate100: '#F1F5F9',
  slate200: '#E2E8F0',
  slate300: '#CBD5E1',
  slate400: '#94A3B8',
  slate500: '#64748B',
  slate600: '#475569',
  slate700: '#334155',
  slate800: '#1E293B',
  slate900: '#0F172A',
  ink: '#080D1A',

  // Brand (indigo)
  brand50: '#EEF2FF',
  brand100: '#E0E7FF',
  brand200: '#C7D2FE',
  brand400: '#818CF8',
  brand500: '#6366F1',
  brand600: '#4F46E5',
  brand700: '#4338CA',

  // Semantic
  green50: '#ECFDF5',
  green500: '#10B981',
  green600: '#059669',
  green700: '#047857',

  amber50: '#FFFBEB',
  amber500: '#F59E0B',
  amber600: '#D97706',
  amber700: '#B45309',

  red50: '#FEF2F2',
  red500: '#EF4444',
  red600: '#DC2626',
  red700: '#B91C1C',
} as const;

export const colors = {
  /** App background */
  background: palette.slate50,
  /** Elevated surface (cards, sheets) */
  surface: palette.white,
  /** Subtle surface used for inset blocks */
  surfaceMuted: palette.slate100,
  /** Dark surface used on splash / camera chrome */
  surfaceDark: palette.slate900,

  border: palette.slate200,
  borderStrong: palette.slate300,

  textPrimary: palette.slate900,
  textSecondary: palette.slate600,
  textTertiary: palette.slate400,
  textInverse: palette.white,
  textInverseMuted: 'rgba(255,255,255,0.72)',

  primary: palette.brand600,
  primaryPressed: palette.brand700,
  primarySoft: palette.brand50,
  primaryBorder: palette.brand200,

  success: palette.green600,
  successSoft: palette.green50,
  successBorder: '#A7F3D0',

  warning: palette.amber600,
  warningSoft: palette.amber50,
  warningBorder: '#FDE68A',

  danger: palette.red600,
  dangerSoft: palette.red50,
  dangerBorder: '#FECACA',

  overlay: 'rgba(8,13,26,0.72)',
  scrim: 'rgba(8,13,26,0.45)',
} as const;

export type SemanticTone = 'neutral' | 'success' | 'warning' | 'danger' | 'primary';

/** Resolves a semantic tone into a background / border / foreground triple. */
export function toneStyles(tone: SemanticTone) {
  switch (tone) {
    case 'success':
      return { bg: colors.successSoft, border: colors.successBorder, fg: palette.green700 };
    case 'warning':
      return { bg: colors.warningSoft, border: colors.warningBorder, fg: palette.amber700 };
    case 'danger':
      return { bg: colors.dangerSoft, border: colors.dangerBorder, fg: palette.red700 };
    case 'primary':
      return { bg: colors.primarySoft, border: colors.primaryBorder, fg: palette.brand700 };
    case 'neutral':
    default:
      return { bg: colors.surfaceMuted, border: colors.border, fg: colors.textSecondary };
  }
}
