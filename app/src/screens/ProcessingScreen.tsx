import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Animated, BackHandler, Easing, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Badge, Button, Card, Screen, Text } from '../components';
import { DEMO_MODE_LABEL } from '../config/demoMode';
import { useScreening } from '../context/ScreeningContext';
import { DEMO_STAGE_COPY, DEMO_STAGE_ORDER } from '../demo/offlineDemoScreening';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Honest waiting copy for the backend path. `POST /api/v1/screen` is a single
 * request/response call with no progress stream, so these lines describe
 * *what is happening* and never claim a step has finished or report a
 * percentage.
 */
const WAITING_LINES: readonly string[] = [
  'Uploading your photos securely…',
  'Checking the submitted documents…',
  'Verifying your identity…',
];

/** How long each waiting line stays on screen. */
const LINE_INTERVAL_MS = 4_000;

/** After this long we say so, rather than looking stuck. */
const SLOW_NOTICE_MS = 20_000;

/**
 * Shown while a verification attempt is running — the backend request, or the
 * on-device offline demo run.
 *
 * Deliberately shows no percentage and no completed-step checklist: in backend
 * mode any such progress would be fiction, and in demo mode the stages are UX
 * states only, not analysis steps. The attempt itself is owned by
 * `ScreeningContext`; this screen only reacts to its outcome — forward to
 * Result on success, back to Review on failure or cancellation.
 */
export function ProcessingScreen({ navigation }: RootStackScreenProps<'Processing'>) {
  const { phase, result, isSubmitting, cancel, isDemoMode, demoStage } = useScreening();
  const pulse = useRef(new Animated.Value(0)).current;

  const [lineIndex, setLineIndex] = useState(0);
  const [slow, setSlow] = useState(false);
  /** Ensures the outcome only ever triggers one navigation. */
  const navigated = useRef(false);
  /**
   * True once a running attempt has actually been observed. Review starts the
   * attempt and navigates here in the same tick, so the very first render can
   * still see `phase === 'idle'`; without this the screen would bounce
   * straight back before the attempt was ever seen.
   */
  const sawSubmitting = useRef(false);

  if (phase === 'submitting') {
    sawSubmitting.current = true;
  }

  /** Leaves Processing for Review without ever emptying the stack. */
  const returnToReview = useCallback(() => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      // Rebuild a sane stack so Review still has somewhere to go back to.
      navigation.reset({ index: 1, routes: [{ name: 'Home' }, { name: 'Review' }] });
    }
  }, [navigation]);

  // Route once the attempt settles. `replace` keeps Processing out of the back
  // stack; a failure or cancellation returns to Review, where the error and
  // the captured images are still available for a retry.
  useEffect(() => {
    if (navigated.current) return;

    if (phase === 'succeeded' && result) {
      navigated.current = true;
      navigation.replace('Result', { result });
      return;
    }

    if (phase === 'failed') {
      navigated.current = true;
      returnToReview();
      return;
    }

    // 'idle' *after* an attempt was seen means it was cancelled or reset;
    // there is nothing left to wait for, so do not sit on a spinner forever.
    // Before that it just means the submit has not landed yet.
    if (phase === 'idle' && sawSubmitting.current) {
      navigated.current = true;
      returnToReview();
    }
    // 'submitting' keeps the honest waiting state on screen; Cancel is always
    // available as an escape hatch.
  }, [navigation, phase, result, returnToReview]);

  const handleCancel = useCallback(() => {
    if (navigated.current) return;
    navigated.current = true;
    // Abort first so a running attempt cannot land after we leave.
    cancel();
    returnToReview();
  }, [cancel, returnToReview]);

  // Android hardware back must not silently drop the screen while an attempt
  // is running; it is routed through the same cancel path as the button.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (isSubmitting) {
        handleCancel();
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [handleCancel, isSubmitting]);

  // Rotate the backend waiting copy so a long wait still looks alive, without
  // ever implying measured progress. Demo mode drives its own stage line.
  useEffect(() => {
    if (!isSubmitting || isDemoMode) return;

    const timer = setInterval(() => {
      setLineIndex((i) => (i + 1) % WAITING_LINES.length);
    }, LINE_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [isDemoMode, isSubmitting]);

  useEffect(() => {
    // The local run is bounded and fast, so a "taking longer" notice would
    // only ever be noise there.
    if (!isSubmitting || isDemoMode) return;

    const timer = setTimeout(() => setSlow(true), SLOW_NOTICE_MS);
    return () => clearTimeout(timer);
  }, [isDemoMode, isSubmitting]);

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.08] });
  const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0.1] });

  // In demo mode the line follows the current stage; the stage list is shown
  // as plain state text, never as a percentage or a completed-step tally.
  const activeStage = demoStage ?? DEMO_STAGE_ORDER[0];
  const statusLine = isDemoMode
    ? DEMO_STAGE_COPY[activeStage]
    : (WAITING_LINES[lineIndex] ?? WAITING_LINES[0]);

  return (
    <Screen
      scroll={false}
      contentStyle={styles.content}
      footer={
        <Button
          label="Cancel verification"
          variant="ghost"
          onPress={handleCancel}
          accessibilityHint={
            isDemoMode
              ? 'Stops the offline demo verification and returns to the review screen'
              : 'Stops the screening request and returns to the review screen'
          }
        />
      }
    >
      <StatusBar style="dark" />

      <View style={styles.center}>
        {isDemoMode ? <Badge label={DEMO_MODE_LABEL} tone="primary" icon="◐" /> : null}

        <View style={styles.spinnerWrap}>
          <Animated.View style={[styles.pulse, { transform: [{ scale }], opacity }]} />
          <View style={styles.spinnerCore}>
            {/* Indeterminate by design — neither path reports progress. */}
            <ActivityIndicator
              size="large"
              color={colors.primary}
              accessibilityLabel="Verification in progress"
            />
          </View>
        </View>

        <Text variant="title" center style={styles.title} accessibilityRole="header">
          Verifying identity
        </Text>

        <Text
          variant="body"
          tone="secondary"
          center
          style={styles.body}
          accessibilityLiveRegion="polite"
        >
          {statusLine}
        </Text>

        <Text variant="caption" tone="tertiary" center style={styles.body}>
          Please keep the app open until the result appears.
        </Text>

        {slow ? (
          <Text
            variant="caption"
            tone="warning"
            center
            style={styles.body}
            accessibilityLiveRegion="polite"
          >
            This is taking longer than usual. The server is still being given time to respond —
            you can cancel and try again if you prefer.
          </Text>
        ) : null}
      </View>

      <Card variant="plain" style={styles.note}>
        <Text variant="caption" tone="secondary" center>
          {isDemoMode
            ? 'Offline demo mode: the flow completes on this device with a fixed demonstration ' +
              'result. No document, face or tampering analysis runs here.'
            : 'Screening runs entirely on the backend. No identity decision is made on this device.'}
        </Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'space-between',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  spinnerWrap: {
    width: 120,
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
    marginTop: spacing.lg,
  },
  pulse: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: radii.pill,
    backgroundColor: colors.primary,
  },
  spinnerCore: {
    width: 76,
    height: 76,
    borderRadius: radii.pill,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    marginTop: spacing.xs,
  },
  body: {
    maxWidth: 320,
  },
  note: {
    marginBottom: spacing.sm,
  },
});
