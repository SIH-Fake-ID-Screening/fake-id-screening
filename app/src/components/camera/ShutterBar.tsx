import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { HIT_SLOP, MIN_TOUCH_SIZE, colors, radii, spacing } from '../../theme';
import { Text } from '../Text';

interface ShutterBarProps {
  onCapture: () => void;
  onCancel: () => void;
  /** Optional right-hand action (e.g. flip camera). Hidden when omitted. */
  onFlip?: () => void;
  busy?: boolean;
  disabled?: boolean;
  /** Accessible description of what will be captured. */
  captureLabel: string;
}

/**
 * Dark camera chrome: cancel on the left, shutter in the middle and an
 * optional flip action on the right. Every target is at least 48dp.
 */
export function ShutterBar({
  onCapture,
  onCancel,
  onFlip,
  busy = false,
  disabled = false,
  captureLabel,
}: ShutterBarProps) {
  const canShoot = !busy && !disabled;

  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Cancel"
        accessibilityHint="Closes the camera and returns to the previous screen"
        onPress={onCancel}
        hitSlop={HIT_SLOP}
        style={({ pressed }) => [styles.sideButton, pressed && styles.sidePressed]}
      >
        <Text variant="bodyStrong" tone="inverse">
          Cancel
        </Text>
      </Pressable>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={captureLabel}
        accessibilityState={{ disabled: !canShoot, busy }}
        onPress={canShoot ? onCapture : undefined}
        disabled={!canShoot}
        hitSlop={HIT_SLOP}
        style={({ pressed }) => [
          styles.shutterRing,
          pressed && canShoot && styles.shutterPressed,
          !canShoot && styles.shutterDisabled,
        ]}
      >
        <View style={styles.shutterCore}>
          {busy ? <ActivityIndicator size="small" color={colors.textPrimary} /> : null}
        </View>
      </Pressable>

      {onFlip ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Switch camera"
          accessibilityHint="Switches between the front and back camera"
          onPress={busy ? undefined : onFlip}
          disabled={busy}
          hitSlop={HIT_SLOP}
          style={({ pressed }) => [styles.sideButton, pressed && styles.sidePressed]}
        >
          <Text variant="bodyStrong" tone="inverse">
            Flip
          </Text>
        </Pressable>
      ) : (
        <View style={styles.sideButton} />
      )}
    </View>
  );
}

const SHUTTER = 74;

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    backgroundColor: colors.surfaceDark,
  },
  sideButton: {
    minWidth: 76,
    minHeight: MIN_TOUCH_SIZE,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
  },
  sidePressed: {
    backgroundColor: 'rgba(255,255,255,0.12)',
  },
  shutterRing: {
    width: SHUTTER,
    height: SHUTTER,
    borderRadius: radii.pill,
    borderWidth: 4,
    borderColor: 'rgba(255,255,255,0.85)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterPressed: {
    borderColor: colors.primary,
  },
  shutterDisabled: {
    opacity: 0.45,
  },
  shutterCore: {
    width: SHUTTER - 18,
    height: SHUTTER - 18,
    borderRadius: radii.pill,
    backgroundColor: colors.textInverse,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
