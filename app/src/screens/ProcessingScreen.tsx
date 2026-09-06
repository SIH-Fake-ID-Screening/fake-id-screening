import React, { useCallback, useEffect, useRef } from 'react';
import { ActivityIndicator, Animated, Easing, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Button, Card, Screen, Text } from '../components';
import { useScreening } from '../context/ScreeningContext';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

/**
 * Shown while the submission is with the backend.
 *
 * Deliberately does NOT claim individual pipeline steps have finished, and
 * shows no percentage: `POST /api/v1/screen` is a single request/response
 * call with no progress stream, so any staged progress bar would be fiction.
 *
 * The request itself is owned by `ScreeningContext`. This screen only reacts
 * to its outcome: forward to Result on success, back to Review on failure.
 */
export function ProcessingScreen({ navigation }: RootStackScreenProps<'Processing'>) {
  const { phase, result, cancel } = useScreening();
  const pulse = useRef(new Animated.Value(0)).current;

  // Route once the real request settles. `replace` keeps Processing out of the
  // back stack; a failure returns to Review, where the error and the captured
  // images are still available for a retry.
  useEffect(() => {
    if (phase === 'succeeded' && result) {
      navigation.replace('Result', { result });
      return;
    }

    if (phase === 'failed') {
      navigation.goBack();
    }
    // 'idle' / 'submitting' keep the honest waiting state on screen; the
    // Cancel action is always available as an escape hatch.
  }, [navigation, phase, result]);

  const handleCancel = useCallback(() => {
    cancel();
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.replace('Review');
    }
  }, [cancel, navigation]);

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

  return (
    <Screen
      scroll={false}
      contentStyle={styles.content}
      footer={
        <Button
          label="Cancel"
          variant="ghost"
          onPress={handleCancel}
          accessibilityHint="Stops the screening request and returns to the review screen"
        />
      }
    >
      <StatusBar style="dark" />

      <View style={styles.center}>
        <View style={styles.spinnerWrap}>
          <Animated.View style={[styles.pulse, { transform: [{ scale }], opacity }]} />
          <View style={styles.spinnerCore}>
            <ActivityIndicator size="large" color={colors.primary} />
          </View>
        </View>

        <Text variant="title" center style={styles.title}>
          Verifying identity
        </Text>
        <Text variant="body" tone="secondary" center style={styles.body}>
          Your documents and selfie are being screened on the secure server. This usually takes a
          few seconds — please keep the app open.
        </Text>
      </View>

      <Card variant="plain" style={styles.note}>
        <Text variant="caption" tone="secondary" center>
          Screening runs entirely on the backend. No identity decision is made on this device.
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
    gap: spacing.md,
  },
  spinnerWrap: {
    width: 120,
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
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
