import React, { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Badge, Button, Card, InfoRow, Screen, Text } from '../components';
import { DEMO_MODE_LABEL } from '../config/demoMode';
import { useCaptures } from '../context/CaptureContext';
import { useScreening } from '../context/ScreeningContext';
import { colors, radii, spacing, toneStyles } from '../theme';
import {
  RISK_LABELS,
  describeSimilarity,
  presentScreeningResult,
  riskBandFor,
  riskTone,
} from '../utils/statusPresentation';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Final screen for one verification attempt.
 *
 * Everything shown here comes from the response passed as a route param —
 * either the real backend response, or the clearly labelled offline demo
 * result, which uses the identical schema so this screen needs no special
 * case. Unknown or malformed statuses are presented as "needs review" by
 * {@link presentScreeningResult} rather than being interpreted as a pass, and
 * every optional field is read defensively so an unexpected payload cannot
 * crash the screen.
 */
export function ResultScreen({ navigation, route }: RootStackScreenProps<'Result'>) {
  const result = route.params?.result ?? null;
  const { reset, clearCapture } = useCaptures();
  const { reset: resetScreening, isDemoMode } = useScreening();

  const presentation = presentScreeningResult(result);
  const tone = toneStyles(presentation.tone);
  const student = result?.student ?? null;
  const face = result?.face_verification ?? null;
  const retry = presentation.retry;

  const risk = riskBandFor(presentation);
  const riskToneStyles = toneStyles(riskTone(risk));
  // Confidence keeps the project's "0.87 of 1.00" convention — it is a
  // similarity score, never a percentage.
  const confidence = face ? describeSimilarity(face.confidence) : null;

  /** Clears everything and returns to Home. */
  const startOver = useCallback(() => {
    reset();
    resetScreening();
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  }, [navigation, reset, resetScreening]);

  /**
   * Runs the recovery action the outcome actually calls for.
   *
   * `recapture` keeps the photos that were fine and only reopens the camera
   * for the implicated one, landing back on Review; `resubmit` keeps all three
   * and returns to Review to send them again; `restart` drops everything.
   */
  const runRetry = useCallback(() => {
    if (!retry) return;

    // The previous result/error must go in every case, so the next attempt
    // starts from a clean submission state.
    resetScreening();

    if (retry.mode === 'restart') {
      reset();
      navigation.reset({
        index: 1,
        routes: [{ name: 'Home' }, { name: 'Capture', params: { slot: 'documentFront' } }],
      });
      return;
    }

    if (retry.mode === 'recapture') {
      clearCapture(retry.slot);
      navigation.reset({
        index: 2,
        routes: [
          { name: 'Home' },
          { name: 'Review' },
          { name: 'Capture', params: { slot: retry.slot, returnTo: 'Review' } },
        ],
      });
      return;
    }

    // 'resubmit' — same three photos, straight back to Review.
    navigation.reset({ index: 1, routes: [{ name: 'Home' }, { name: 'Review' }] });
  }, [clearCapture, navigation, reset, resetScreening, retry]);

  const screeningId =
    typeof result?.screening_id === 'string' && result.screening_id.trim().length > 0
      ? result.screening_id.trim()
      : null;

  const serverNote =
    typeof result?.message === 'string' && result.message.trim().length > 0
      ? result.message.trim()
      : null;

  return (
    <Screen
      footer={
        <>
          {retry ? (
            <Button
              label={retry.label}
              icon="↻"
              onPress={runRetry}
              accessibilityHint={
                retry.mode === 'recapture'
                  ? 'Reopens the camera for the photo that needs replacing'
                  : retry.mode === 'resubmit'
                    ? 'Returns to review so the same photos can be submitted again'
                    : 'Starts a brand new verification from the first photo'
              }
            />
          ) : null}
          <Button
            label="Done"
            variant={retry ? 'secondary' : 'primary'}
            onPress={startOver}
            accessibilityHint="Clears this session's photos and returns to the start"
          />
        </>
      }
    >
      <StatusBar style="dark" />

      {/* Subtle, single mode marker so a demo result is never mistaken for a
          real backend screening decision. */}
      {isDemoMode ? (
        <Badge label={DEMO_MODE_LABEL} tone="primary" icon="◐" style={styles.modeBadge} />
      ) : null}

      {/* Verdict banner */}
      <View
        style={[styles.verdict, { backgroundColor: tone.bg, borderColor: tone.border }]}
        accessibilityLiveRegion="polite"
      >
        <View style={[styles.verdictIcon, { borderColor: tone.border }]}>
          <Text style={[styles.verdictGlyph, { color: tone.fg }]} accessibilityElementsHidden>
            {presentation.icon}
          </Text>
        </View>

        <Text variant="title" center style={{ color: tone.fg }} accessibilityRole="header">
          {presentation.title}
        </Text>
        <Text variant="body" center style={[styles.verdictBody, { color: tone.fg }]}>
          {presentation.summary}
        </Text>
      </View>

      {/* Headline figures. Each carries a text label as well as its tone, so
          nothing here is conveyed by colour alone. */}
      <Card style={styles.block}>
        <Text variant="label" tone="tertiary">
          Verification summary
        </Text>

        <View style={styles.summaryRow}>
          <Text variant="caption" tone="secondary" style={styles.summaryLabel}>
            Confidence
          </Text>
          <Text
            variant="bodyStrong"
            style={styles.summaryValue}
            accessibilityLabel={
              confidence
                ? `Confidence ${confidence.score} of 1.00`
                : 'Confidence not available'
            }
          >
            {confidence ? `${confidence.score} of 1.00` : 'Not available'}
          </Text>
        </View>

        <View style={styles.summaryRow}>
          <Text variant="caption" tone="secondary" style={styles.summaryLabel}>
            Risk
          </Text>
          <View style={styles.summaryValueWrap}>
            <Badge
              label={RISK_LABELS[risk]}
              tone={riskTone(risk)}
              icon={risk === 'low' ? '✓' : risk === 'high' ? '✕' : '!'}
              style={styles.riskBadge}
            />
          </View>
        </View>

        <Text variant="caption" tone="tertiary" style={{ color: riskToneStyles.fg }}>
          {risk === 'low'
            ? 'Risk band reflects the reported outcome for this attempt.'
            : 'Risk band reflects the reported outcome — treat this attempt as unconfirmed.'}
        </Text>
      </Card>

      {/* Recommended action */}
      <Card variant="plain" style={styles.block}>
        <Text variant="label" tone="tertiary">
          What to do next
        </Text>
        <Text variant="body" tone="secondary">
          {presentation.advice}
        </Text>
      </Card>

      {/* Face verification detail */}
      {presentation.showFaceDetails && face ? (
        <Card style={styles.block}>
          <View style={styles.blockHeader}>
            <Text variant="subheading">Face verification</Text>
            <Badge
              label={face.match ? 'Match' : 'No match'}
              tone={face.match ? 'success' : 'danger'}
              icon={face.match ? '✓' : '✕'}
            />
          </View>

          {(() => {
            const similarity = describeSimilarity(face.confidence);
            return (
              <>
                <InfoRow label="Similarity band" value={similarity.band} emphasis />
                <InfoRow
                  label="Similarity score"
                  value={`${similarity.score} of 1.00`}
                  divider={false}
                />
                <Text variant="caption" tone="tertiary" style={styles.footnote}>
                  Score is the similarity between the live selfie and the institution's reference
                  photo. It is a comparison measure, not a probability.
                </Text>
              </>
            );
          })()}
        </Card>
      ) : null}

      {/* Student record */}
      {presentation.showStudentDetails && student ? (
        <Card style={styles.block}>
          <View style={styles.blockHeader}>
            <Text variant="subheading">Student record</Text>
            {student.blacklisted ? <Badge label="Blacklisted" tone="danger" icon="⛔" /> : null}
          </View>

          <InfoRow label="Name" value={emptyToNull(student.name)} emphasis />
          <InfoRow label="Student ID" value={emptyToNull(student.student_id)} />
          <InfoRow label="Course" value={student.course} />
          <InfoRow label="College" value={student.college} />
          <InfoRow label="Date of birth" value={student.dob} />
          <InfoRow label="Valid till" value={student.valid_till} />
          <InfoRow
            label="Record status"
            value={formatRecordStatus(student.status)}
            divider={false}
          />
        </Card>
      ) : null}

      {/* Reference for support / audit */}
      <Card variant="plain" style={styles.block}>
        <Text variant="label" tone="tertiary">
          Screening reference
        </Text>
        <Text variant="mono" tone="secondary" selectable style={styles.reference}>
          {screeningId ?? 'Not provided'}
        </Text>
        {serverNote ? (
          <Text variant="caption" tone="tertiary">
            {isDemoMode ? 'Note' : 'Server note'}: {serverNote}
          </Text>
        ) : null}
        {/* Raw status is surfaced only when this app version cannot interpret
            it, so an unrecognised outcome stays reportable rather than lost. */}
        {presentation.outcome === 'inconclusive' && presentation.tone === 'neutral' ? (
          <Text variant="caption" tone="tertiary">
            Reported status: {describeRawStatus(result?.status)}
          </Text>
        ) : null}
      </Card>
    </Screen>
  );
}

/** Treats a blank backend string as "no value" so InfoRow shows its dash. */
function emptyToNull(value: string | null | undefined): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

/** Turns a raw record status like "active" into display copy. */
function formatRecordStatus(status: string | undefined): string | null {
  if (typeof status !== 'string' || status.trim().length === 0) return null;
  const normalised = status.trim().toLowerCase();
  const labels: Record<string, string> = {
    active: 'Active',
    expired: 'Expired',
    suspended: 'Suspended',
    inactive: 'Inactive',
  };
  return labels[normalised] ?? status.trim();
}

/** Renders an unrecognised status safely, whatever type it arrived as. */
function describeRawStatus(status: unknown): string {
  if (typeof status === 'string' && status.trim().length > 0) return status.trim();
  return 'unknown';
}

const styles = StyleSheet.create({
  modeBadge: {
    marginBottom: spacing.md,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.lg,
    paddingVertical: spacing.sm,
  },
  summaryLabel: {
    flexShrink: 0,
  },
  summaryValue: {
    flexShrink: 1,
    textAlign: 'right',
  },
  summaryValueWrap: {
    alignItems: 'flex-end',
  },
  riskBadge: {
    alignSelf: 'flex-end',
  },
  verdict: {
    borderRadius: radii.xxl,
    borderWidth: 1,
    paddingVertical: spacing.xxl,
    paddingHorizontal: spacing.xl,
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  verdictIcon: {
    width: 64,
    height: 64,
    borderRadius: radii.pill,
    borderWidth: 2,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  verdictGlyph: {
    fontSize: 30,
  },
  verdictBody: {
    maxWidth: 320,
  },
  block: {
    marginBottom: spacing.lg,
    gap: spacing.sm,
  },
  blockHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  footnote: {
    marginTop: spacing.sm,
  },
  reference: {
    color: colors.textPrimary,
  },
});
