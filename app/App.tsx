import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { CaptureProvider } from './src/context/CaptureContext';
import { ScreeningProvider } from './src/context/ScreeningContext';
import { RootNavigator } from './src/navigation/RootNavigator';

export default function App() {
  return (
    <SafeAreaProvider>
      <CaptureProvider>
        {/* Owns the single screening request; nested so it can read captures. */}
        <ScreeningProvider>
          <StatusBar style="dark" />
          <RootNavigator />
        </ScreeningProvider>
      </CaptureProvider>
    </SafeAreaProvider>
  );
}
