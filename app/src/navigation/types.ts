import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { CaptureSlot, ScreeningResponse } from '../types/screening';

/**
 * Route map for the single native stack.
 *
 * Flow: Splash → Home → Capture(front) → Capture(back) → Capture(selfie)
 *       → Review → Processing → Result
 */
export type RootStackParamList = {
  Splash: undefined;
  Home: undefined;
  /**
   * `returnTo` marks a capture opened from Review (a retake or a fill-in for a
   * missing slot). It is passed explicitly rather than inferred from the
   * navigation stack, so back-navigation cannot make the Capture screen guess
   * the wrong destination.
   */
  Capture: { slot: CaptureSlot; returnTo?: 'Review' };
  Review: undefined;
  Processing: undefined;
  Result: { result: ScreeningResponse };
};

export type RootStackScreenProps<T extends keyof RootStackParamList> = NativeStackScreenProps<
  RootStackParamList,
  T
>;

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
