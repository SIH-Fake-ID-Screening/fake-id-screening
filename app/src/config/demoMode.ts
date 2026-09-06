import { isApiConfigured } from './env';

export type ScreeningMode = 'offline_demo' | 'backend';

/**
 * The mobile demo is intentionally offline when no backend URL is configured.
 *
 * A configured API URL opts into the real backend path. This keeps the app
 * usable for an offline SIH demonstration while preserving the production
 * integration for later.
 */
export function resolveScreeningMode(): ScreeningMode {
  return isApiConfigured() ? 'backend' : 'offline_demo';
}

export const DEMO_MODE_LABEL = 'Offline Demo Mode';

export const DEMO_MODE_SHORT_NOTE =
  'Runs locally without uploading your captured images.';

export const DEMO_MODE_NOTE =
  'Offline demonstration only. No images are uploaded or sent to a server.';

export const DEMO_TRUST_POINTS = [
  {
    icon: '📱',
    title: 'Works offline',
    body: 'Demo verification runs locally on this device.',
  },
  {
    icon: '🔐',
    title: 'Images stay local',
    body: 'Captured images are not uploaded in demo mode.',
  },
  {
    icon: '⚡',
    title: 'Instant demonstration',
    body: 'The verification flow works without a server connection.',
  },
] as const;
