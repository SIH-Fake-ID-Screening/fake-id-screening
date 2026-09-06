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
  Capture: { slot: CaptureSlot };
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
