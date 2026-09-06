# VerifID — Mobile App

Android-focused mobile client for the SIH project **AI-Based Fake Identity & Document Screening System**.

> This directory contains **only** the mobile application. The backend, web frontend and
> AI modules live elsewhere in the repository and are treated as read-only by this app.

## What this app does

The app is a **thin client**. It captures the three inputs the screening pipeline needs,
submits them to the existing backend, and presents the outcome:

1. Front of the student ID card
2. Back of the student ID card
3. A live selfie

All screening logic — OCR, database lookup, expiry validation and face verification —
runs **server-side**. The app deliberately performs **no** OCR, face matching, tamper
detection or blockchain work locally.

### Backend contract

```
POST /api/v1/screen        multipart/form-data
  document_front           image/jpeg | image/png, max 10 MB
  document_back            image/jpeg | image/png, max 10 MB
  live_photo               image/jpeg | image/png, max 10 MB
```

Response shape and status values are mirrored in [`src/types/screening.ts`](src/types/screening.ts),
derived from `backend/schemas/screening.py`.

## Tech stack

- Expo (React Native) + TypeScript, strict mode
- React Navigation (native stack)
- `expo-camera` for capture, `expo-image-manipulator` for upload preparation

## Getting started

```bash
cd app
npm install
npm run android      # or: npm start, then scan the QR code with Expo Go
```

Useful scripts:

| Script              | Purpose                          |
| ------------------- | -------------------------------- |
| `npm start`         | Start the Expo dev server        |
| `npm run android`   | Launch on an Android device/emulator |
| `npm run typecheck` | TypeScript check (`tsc --noEmit`) |

## Project structure

```
app/
├── App.tsx                  # Root: providers + navigator
├── src/
│   ├── components/          # Design-system primitives (Button, Card, Text, …)
│   ├── constants/           # Product copy and capture-step metadata
│   ├── context/             # In-memory capture state for one session
│   ├── navigation/          # Native stack + route param types
│   ├── screens/             # Splash, Home, Capture, Review, Processing, Result
│   ├── theme/               # Colour, spacing, typography, elevation tokens
│   ├── types/               # Backend API types
│   └── utils/               # Status → user-facing copy mapping
```

## User flow

```
Splash → Home → ID front → ID back → Live selfie → Review → Processing → Result
```

The Review step exists so nothing is uploaded by accident; any single photo can be
retaken from there.

## Design notes

- **Honest progress.** The processing screen never claims individual backend pipeline
  steps have completed, because the app has no visibility into server-side progress.
- **No raw status strings.** Backend statuses are mapped to plain-language explanations
  in `src/utils/statusPresentation.ts`. Unrecognised statuses fall back to a safe
  "needs review" state rather than being shown as a pass.
- **Similarity, not probability.** The backend's `confidence` is a cosine similarity
  between face embeddings, so it is shown as a score out of 1.00 with a descriptive
  band — never mislabelled as a percentage likelihood.
- **Nothing persisted.** Captured images are held in memory for the session only.

## Privacy

Captured ID images and selfies are never written to app storage and are discarded when
the flow is reset. They are transmitted only to the configured screening backend.
