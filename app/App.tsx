import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { CaptureProvider } from './src/context/CaptureContext';
import { RootNavigator } from './src/navigation/RootNavigator';

export default function App() {
  return (
    <SafeAreaProvider>
      <CaptureProvider>
        <StatusBar style="dark" />
        <RootNavigator />
      </CaptureProvider>
    </SafeAreaProvider>
  );
}
