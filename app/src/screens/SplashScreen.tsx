import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import { Text } from '../components';
import { APP_NAME, APP_TAGLINE, ORGANISATION } from '../constants/app';
import { colors, palette, radii, spacing } from '../theme';
import type { RootStackScreenProps } from '../navigation/types';

const SPLASH_DURATION_MS = 1500;

/**
 * Brand entry screen. A single short fade/rise — enough to feel finished
 * without delaying the demo.
 */
export function SplashScreen({ navigation }: RootStackScreenProps<'Splash'>) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(12)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 420,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: 420,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]).start();

    const timer = setTimeout(() => {
      navigation.replace('Home');
    }, SPLASH_DURATION_MS);

    return () => clearTimeout(timer);
  }, [navigation, opacity, translateY]);

  return (
    <View style={styles.root}>
      <StatusBar style="light" />
      <SafeAreaView style={styles.safe}>
        <Animated.View style={[styles.center, { opacity, transform: [{ translateY }] }]}>
          <View style={styles.mark}>
            <Text style={styles.markGlyph}>🛡</Text>
          </View>

          <Text variant="title" tone="inverse" center style={styles.name}>
            {APP_NAME}
          </Text>
          <Text variant="body" tone="inverseMuted" center style={styles.tagline}>
            {APP_TAGLINE}
          </Text>
        </Animated.View>

        <Animated.View style={{ opacity }}>
          <Text variant="label" tone="inverseMuted" center>
            {ORGANISATION}
          </Text>
        </Animated.View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.surfaceDark,
  },
  safe: {
    flex: 1,
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.huge,
    paddingHorizontal: spacing.xl,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  mark: {
    width: 88,
    height: 88,
    borderRadius: radii.xxl,
    backgroundColor: palette.brand600,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  markGlyph: {
    fontSize: 42,
    color: colors.textInverse,
  },
  name: {
    maxWidth: 320,
  },
  tagline: {
    maxWidth: 300,
  },
});
