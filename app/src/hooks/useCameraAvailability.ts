import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { CameraView } from 'expo-camera';

type Availability = 'checking' | 'available' | 'unavailable';

/**
 * `CameraView.isAvailableAsync()` is only meaningful on web (and simulators),
 * where a browser may expose no video input at all. On native we assume a
 * camera exists and rely on `onMountError` to surface real hardware failures.
 */
export function useCameraAvailability(): Availability {
  const [availability, setAvailability] = useState<Availability>(
    Platform.OS === 'web' ? 'checking' : 'available',
  );

  useEffect(() => {
    if (Platform.OS !== 'web') {
      return;
    }

    let cancelled = false;

    CameraView.isAvailableAsync()
      .then((ok) => {
        if (!cancelled) {
          setAvailability(ok ? 'available' : 'unavailable');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAvailability('unavailable');
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return availability;
}
