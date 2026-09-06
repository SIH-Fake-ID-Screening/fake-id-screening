import React from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Badge, Button, Card, Screen, Text } from '../components';
import { APP_NAME, APP_TAGLINE, ORGANISATION, TRUST_POINTS } from '../constants/app';
import { CAPTURE_SLOTS } from '../constants/captureSlots';
import { useCaptures } from '../context/CaptureContext';
import { useScreening } from '../context/ScreeningContext';
import { colors, palette, radii, shadows, spacing, toneStyles } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

export function HomeScreen({ navigation }: RootStackScreenProps<'Home'>) {
  const { reset } = useCaptures();
  const { reset: resetScreening, isConfigured } = useScreening();
  const warningTone = toneStyles('warning');

  const startVerification = () => {
    // Always begin from a clean slate so a previous run can't leak images
    // or show a stale result/error.
    reset();
    resetScreening();
    navigation.navigate('Capture', { slot: 'documentFront' });
  };

  return (
    <Screen
      footer={
        <>
          <Button
            label="Start Verification"
            icon="→"
            onPress={startVerification}
            accessibilityHint="Begins the three-step identity verification flow"
          />
          <Text variant="caption" tone="tertiary" center>
            {isConfigured
              ? 'Takes about a minute · 3 photos required'
              : 'Screening server not configured — submission will be blocked at the end.'}
          </Text>
        </>
      }
    >
      <StatusBar style="dark" />

      {/* Header / branding */}
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <View style={styles.mark}>
            <Text style={styles.markGlyph}>🛡</Text>
          </View>
          <View style={styles.brandText}>
            <Text variant="heading">{APP_NAME}</Text>
            <Text variant="caption" tone="secondary">
              {ORGANISATION}
            </Text>
          </View>
        </View>
      </View>

      {/* Missing configuration is announced here rather than only at the end,
          so a demo is not set up three photos deep before it fails. */}
      {!isConfigured ? (
        <View
          style={[
            styles.configNotice,
            { backgroundColor: warningTone.bg, borderColor: warningTone.border },
          ]}
          accessibilityRole="alert"
        >
          <Text variant="label" style={{ color: warningTone.fg }}>
            Screening server not configured
          </Text>
          <Text variant="caption" style={{ color: warningTone.fg }}>
            Photos can be captured, but nothing can be screened until
            EXPO_PUBLIC_API_BASE_URL points at the backend. See app/README.md.
          </Text>
        </View>
      ) : null}

      {/* Hero */}
      <View style={styles.hero}>
        <Badge label="AI-powered screening" tone="primary" icon="◆" />
        <Text variant="display" style={styles.heroTitle}>
          Verify an identity in three steps
        </Text>
        <Text variant="body" tone="secondary">
          {APP_TAGLINE}. Capture your ID card and a live selfie — the secure backend extracts the
          document details, checks them against institutional records and confirms the face match.
        </Text>
      </View>

      {/* The three required inputs */}
      <Card style={styles.section}>
        <Text variant="label" tone="tertiary">
          What you'll need
        </Text>

        <View style={styles.stepList}>
          {CAPTURE_SLOTS.map((meta, index) => (
            <View key={meta.slot} style={styles.stepRow}>
              <View style={styles.stepNumber}>
                <Text variant="caption" style={styles.stepNumberText}>
                  {index + 1}
                </Text>
              </View>
              <View style={styles.stepBody}>
                <Text variant="bodyStrong">{meta.title}</Text>
                <Text variant="caption" tone="secondary">
                  {meta.description}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </Card>

      {/* Trust / security messaging */}
      <View style={styles.section}>
        <Text variant="label" tone="tertiary" style={styles.sectionLabel}>
          How your data is handled
        </Text>

        <View style={styles.trustList}>
          {TRUST_POINTS.map((point) => (
            <Card key={point.title} variant="plain" style={styles.trustCard}>
              <Text style={styles.trustIcon}>{point.icon}</Text>
              <View style={styles.trustBody}>
                <Text variant="bodyStrong">{point.title}</Text>
                <Text variant="caption" tone="secondary">
                  {point.body}
                </Text>
              </View>
            </Card>
          ))}
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: spacing.xxl,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  mark: {
    width: 44,
    height: 44,
    borderRadius: radii.md,
    backgroundColor: palette.brand600,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.card,
  },
  markGlyph: {
    fontSize: 22,
    color: colors.textInverse,
  },
  brandText: {
    flex: 1,
  },
  configNotice: {
    borderRadius: radii.lg,
    borderWidth: 1,
    padding: spacing.lg,
    gap: spacing.xs,
    marginBottom: spacing.xl,
  },
  hero: {
    gap: spacing.md,
    marginBottom: spacing.xxl,
  },
  heroTitle: {
    marginTop: spacing.xs,
  },
  section: {
    marginBottom: spacing.xl,
    gap: spacing.md,
  },
  sectionLabel: {
    marginBottom: spacing.xs,
  },
  stepList: {
    gap: spacing.lg,
  },
  stepRow: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'flex-start',
  },
  stepNumber: {
    width: 26,
    height: 26,
    borderRadius: radii.pill,
    backgroundColor: colors.primarySoft,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNumberText: {
    color: palette.brand700,
    fontWeight: '700',
  },
  stepBody: {
    flex: 1,
    gap: spacing.xxs,
  },
  trustList: {
    gap: spacing.md,
  },
  trustCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
  },
  trustIcon: {
    fontSize: 18,
  },
  trustBody: {
    flex: 1,
    gap: spacing.xxs,
  },
});
