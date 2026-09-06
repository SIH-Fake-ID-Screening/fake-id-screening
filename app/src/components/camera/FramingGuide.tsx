import React from 'react';
import { StyleSheet, View } from 'react-native';

import { colors, radii, spacing } from '../../theme';
import { Text } from '../Text';

export type GuideShape = 'card' | 'face';

interface FramingGuideProps {
  shape: GuideShape;
  /** Short instruction rendered under the cut-out. */
  hint?: string;
  /** Highlights the guide (e.g. while the shutter is busy). */
  active?: boolean;
}

/**
 * Non-interactive framing overlay drawn on top of the camera preview.
 *
 * A scrim with a transparent cut-out is faked with four translucent panels so
 * no masking library is required, which keeps the Android layout predictable.
 */
export function FramingGuide({ shape, hint, active = false }: FramingGuideProps) {
  const isFace = shape === 'face';

  return (
    <View pointerEvents="none" style={styles.root} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {/* Top scrim */}
      <View style={styles.scrim} />

      <View style={styles.middleRow}>
        <View style={[styles.scrim, styles.sideScrim]} />

        <View style={[styles.window, isFace ? styles.windowFace : styles.windowCard]}>
          <View
            style={[
              styles.frame,
              isFace ? styles.frameFace : styles.frameCard,
              active && styles.frameActive,
            ]}
          >
            {isFace ? null : <Corners />}
          </View>
        </View>

        <View style={[styles.scrim, styles.sideScrim]} />
      </View>

      {/* Bottom scrim carries the hint so it never overlaps the cut-out */}
      <View style={[styles.scrim, styles.bottomScrim]}>
        {hint ? (
          <Text variant="caption" tone="inverseMuted" center style={styles.hint}>
            {hint}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

/** Four L-shaped corner ticks that read as a document viewfinder. */
function Corners() {
  return (
    <>
      <View style={[styles.corner, styles.cornerTopLeft]} />
      <View style={[styles.corner, styles.cornerTopRight]} />
      <View style={[styles.corner, styles.cornerBottomLeft]} />
      <View style={[styles.corner, styles.cornerBottomRight]} />
    </>
  );
}

const SCRIM = 'rgba(8,13,26,0.55)';
const CORNER = 22;

const styles = StyleSheet.create({
  root: {
    ...StyleSheet.absoluteFill,
  },
  scrim: {
    flex: 1,
    backgroundColor: SCRIM,
  },
  middleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sideScrim: {
    alignSelf: 'stretch',
  },
  bottomScrim: {
    justifyContent: 'flex-start',
    paddingTop: spacing.lg,
    paddingHorizontal: spacing.xl,
  },
  window: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  windowCard: {
    width: '88%',
    aspectRatio: 1.58, // ID-1 card ratio
  },
  windowFace: {
    width: '68%',
    aspectRatio: 0.78,
  },
  frame: {
    flex: 1,
    alignSelf: 'stretch',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.9)',
  },
  frameCard: {
    borderRadius: radii.lg,
  },
  frameFace: {
    borderRadius: radii.pill,
    borderStyle: 'dashed',
  },
  frameActive: {
    borderColor: colors.primary,
  },
  hint: {
    maxWidth: 320,
    alignSelf: 'center',
  },
  corner: {
    position: 'absolute',
    width: CORNER,
    height: CORNER,
    borderColor: colors.textInverse,
  },
  cornerTopLeft: {
    top: -2,
    left: -2,
    borderTopWidth: 4,
    borderLeftWidth: 4,
    borderTopLeftRadius: radii.lg,
  },
  cornerTopRight: {
    top: -2,
    right: -2,
    borderTopWidth: 4,
    borderRightWidth: 4,
    borderTopRightRadius: radii.lg,
  },
  cornerBottomLeft: {
    bottom: -2,
    left: -2,
    borderBottomWidth: 4,
    borderLeftWidth: 4,
    borderBottomLeftRadius: radii.lg,
  },
  cornerBottomRight: {
    bottom: -2,
    right: -2,
    borderBottomWidth: 4,
    borderRightWidth: 4,
    borderBottomRightRadius: radii.lg,
  },
});
