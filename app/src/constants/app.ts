/** Product-level strings used across the app. */

export const APP_NAME = 'VerifID';
export const APP_TAGLINE = 'AI-based fake identity & document screening';
export const ORGANISATION = 'Smart India Hackathon';

export interface TrustPoint {
  icon: string;
  title: string;
  body: string;
}

/** Trust markers shown on the home screen when a backend is configured. */
export const TRUST_POINTS: readonly TrustPoint[] = [
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

/**
 * Trust markers used in offline demo mode.
 *
 * These describe the demo path truthfully: the flow completes on the device
 * with a fixed demonstration result, and no analysis of any kind runs here.
 */
export const DEMO_TRUST_POINTS: readonly TrustPoint[] = [
  {
    icon: '📴',
    title: 'Works without a network',
    body: 'The flow completes on this device. No photos are uploaded and no server is contacted.',
  },
  {
    icon: '🎬',
    title: 'Demonstration result',
    body: 'The outcome is a fixed sample. No document reading, face matching or tampering analysis runs on this device.',
  },
  {
    icon: '🕓',
    title: 'Nothing stored locally',
    body: 'Captured images are held in memory for this session only and cleared afterwards.',
  },
] as const;
