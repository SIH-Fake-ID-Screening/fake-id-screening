import React, { useEffect, useRef } from 'react';
import { ActivityIndicator, Animated, Easing, StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { Button, Card, Screen, Text } from '../components';
import { colors, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';
import type { ScreeningResponse } from '../types/screening';

/**
 * Dev-only sample payload so the result screen can be inspected before the
 * real API call is wired up in Milestone 4. Never used in a release build.
 */
const DEV_PREVIEW_RESULT: ScreeningResponse = {
  screening_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
  status: 'completed',
  student: {
    student_id: '202501100600212',
    name: 'Priyanshu Ranjan',
    course: 'B.Tech Information Technology',
    college: 'KIET Group of Institutions',
    dob: '2005-04-18',
    valid_till: '2029-07-01',
    status: 'active',
    blacklisted: false,
  },
  face_verification: { match: true, confidence: 0.87 },
  message: 'Face verification completed.',
};

/**
 * Shown while the submission is with the backend.
 *
 * Deliberately does NOT claim individual pipeline steps have finished — the
 * app has no visibility into backend progress, so it shows honest, general
 * status copy only.
 *
 * MILESTONE 1: static loading state. The real upload request, timeout, error
 * and retry handling are added in Milestone 4.
 */
export function ProcessingScreen({ navigation }: RootStackScreenProps<'Processing'>) {
  const pulse = useRef(new Animated.Value(0)).current;

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
        <>
          {__DEV__ ? (
            <Button
              label="Preview result screen (dev)"
              variant="secondary"
              size="md"
              onPress={() => navigation.replace('Result', { result: DEV_PREVIEW_RESULT })}
            />
          ) : null}
          <Button
            label="Cancel"
            variant="ghost"
            onPress={() => navigation.goBack()}
            accessibilityHint="Stops waiting and returns to the review screen"
          />
        </>
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
