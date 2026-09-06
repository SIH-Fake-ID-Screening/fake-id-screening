import React from 'react';
import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Badge, Button, Card, InfoRow, Screen, Text } from '../components';
import { useCaptures } from '../context/CaptureContext';
import { useScreening } from '../context/ScreeningContext';
import { colors, radii, spacing, toneStyles } from '../theme';
import { describeSimilarity, presentScreeningResult } from '../utils/statusPresentation';
import type { RootStackScreenProps } from '../navigation/types';

export function ResultScreen({ navigation, route }: RootStackScreenProps<'Result'>) {
  const { result } = route.params;
  const { reset } = useCaptures();
  const { reset: resetScreening } = useScreening();

  const presentation = presentScreeningResult(result);
  const tone = toneStyles(presentation.tone);
  const student = result?.student ?? null;
  const face = result?.face_verification ?? null;

  const startOver = () => {
    reset();
    resetScreening();
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  };

  const retry = () => {
    reset();
    resetScreening();
    navigation.reset({
      index: 1,
      routes: [{ name: 'Home' }, { name: 'Capture', params: { slot: 'documentFront' } }],
    });
  };

  return (
    <Screen
      footer={
        <>
          {presentation.allowRetry ? (
            <Button label="Try again" icon="↻" onPress={retry} />
          ) : null}
          <Button
            label="Done"
            variant={presentation.allowRetry ? 'secondary' : 'primary'}
            onPress={startOver}
          />
        </>
      }
    >
      <StatusBar style="dark" />

      {/* Verdict banner */}
      <View style={[styles.verdict, { backgroundColor: tone.bg, borderColor: tone.border }]}>
        <View style={[styles.verdictIcon, { borderColor: tone.border }]}>
          <Text style={[styles.verdictGlyph, { color: tone.fg }]}>{presentation.icon}</Text>
        </View>

        <Text variant="title" center style={{ color: tone.fg }}>
          {presentation.title}
        </Text>
        <Text variant="body" center style={[styles.verdictBody, { color: tone.fg }]}>
          {presentation.summary}
        </Text>
      </View>

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

          <InfoRow label="Name" value={student.name} emphasis />
          <InfoRow label="Student ID" value={student.student_id} />
          <InfoRow label="Course" value={student.course} />
          <InfoRow label="College" value={student.college} />
          <InfoRow label="Date of birth" value={student.dob} />
          <InfoRow label="Valid till" value={student.valid_till} />
          <InfoRow label="Record status" value={formatRecordStatus(student.status)} divider={false} />
        </Card>
      ) : null}

      {/* Reference for support / audit */}
      <Card variant="plain" style={styles.block}>
        <Text variant="label" tone="tertiary">
          Screening reference
        </Text>
        <Text variant="mono" tone="secondary" selectable style={styles.reference}>
          {typeof result?.screening_id === 'string' && result.screening_id.length > 0
            ? result.screening_id
            : 'Not provided'}
        </Text>
        {typeof result?.message === 'string' && result.message.trim().length > 0 ? (
          <Text variant="caption" tone="tertiary">
            Server note: {result.message.trim()}
          </Text>
        ) : null}
        {/* Raw status is surfaced only when this app version cannot interpret
            it, so an unrecognised outcome stays reportable rather than lost. */}
        {presentation.outcome === 'inconclusive' && presentation.tone === 'neutral' ? (
          <Text variant="caption" tone="tertiary">
            Reported status: {String(result?.status ?? 'unknown')}
          </Text>
        ) : null}
      </Card>
    </Screen>
  );
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

const styles = StyleSheet.create({
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
