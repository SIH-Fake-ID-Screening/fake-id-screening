/** Product-level strings used across the app. */

export const APP_NAME = 'VerifID';
export const APP_TAGLINE = 'AI-based fake identity & document screening';
export const ORGANISATION = 'Smart India Hackathon';

/** Trust markers shown on the home screen. */
export const TRUST_POINTS: readonly { icon: string; title: string; body: string }[] = [
  {
    icon: '🔒',
    title: 'Server-side verification',
    body: 'Screening runs on the secure backend. No identity checks happen on this device.',
  },
  {
    icon: '🗄',
    title: 'Trusted reference data',
    body: 'Your face is matched against the official institutional record, not the uploaded card.',
  },
  {
    icon: '🕓',
    title: 'Nothing stored locally',
    body: 'Captured images are held in memory for this session only and cleared afterwards.',
  },
] as const;
