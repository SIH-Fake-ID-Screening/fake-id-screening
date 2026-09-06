import type { CaptureSlot } from '../types/screening';

/**
 * Static, presentation-level metadata for each required input.
 * Keeping this in one place means the Home, Review and Camera screens all
 * describe the same three steps with identical wording.
 */
export interface CaptureSlotMeta {
  slot: CaptureSlot;
  /** Short label used in chips and lists. */
  label: string;
  /** Screen title. */
  title: string;
  /** One-line explanation shown to the user. */
  description: string;
  /** The multipart field name expected by POST /api/v1/screen. */
  field: 'document_front' | 'document_back' | 'live_photo';
  /** Which physical camera to open. */
  facing: 'back' | 'front';
  /** Framing guide shape. */
  guide: 'card' | 'face';
  /** Bulleted capture tips. */
  tips: string[];
}

export const CAPTURE_SLOTS: readonly CaptureSlotMeta[] = [
  {
    slot: 'documentFront',
    label: 'ID front',
    title: 'Front of ID card',
    description: 'Capture the side showing your photo, name and student ID.',
    field: 'document_front',
    facing: 'back',
    guide: 'card',
    tips: [
      'Fit the whole card inside the frame',
      'Avoid glare and hard shadows',
      'Keep the text sharp and readable',
    ],
  },
  {
    slot: 'documentBack',
    label: 'ID back',
    title: 'Back of ID card',
    description: 'Capture the reverse side, including the validity details.',
    field: 'document_back',
    facing: 'back',
    guide: 'card',
    tips: [
      'Fit the whole card inside the frame',
      'Make sure the validity date is visible',
      'Hold steady until the shot is taken',
    ],
  },
  {
    slot: 'livePhoto',
    label: 'Live selfie',
    title: 'Live selfie',
    description: 'Take a live photo so your face can be verified.',
    field: 'live_photo',
    facing: 'front',
    guide: 'face',
    tips: [
      'Centre your face in the circle',
      'Use even, front-facing light',
      'Remove sunglasses, caps and masks',
    ],
  },
] as const;

export const CAPTURE_SLOT_MAP: Record<CaptureSlot, CaptureSlotMeta> = CAPTURE_SLOTS.reduce(
  (acc, meta) => {
    acc[meta.slot] = meta;
    return acc;
  },
  {} as Record<CaptureSlot, CaptureSlotMeta>,
);

export const CAPTURE_ORDER: readonly CaptureSlot[] = CAPTURE_SLOTS.map((m) => m.slot);
