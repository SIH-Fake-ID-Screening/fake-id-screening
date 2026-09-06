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
cp .env.example .env  # then set EXPO_PUBLIC_API_BASE_URL (see below)
npm run android       # or: npm start, then scan the QR code with Expo Go
```

## Configuring the backend URL

The app has **no built-in server address**. The backend is not deployed yet, so the
screening host is supplied per-environment via an Expo public environment variable:

| Variable                     | Required | Purpose                                                       |
| ---------------------------- | -------- | ------------------------------------------------------------- |
| `EXPO_PUBLIC_API_BASE_URL`   | yes      | Backend origin, e.g. `http://192.168.1.20:8000`               |
| `EXPO_PUBLIC_API_TIMEOUT_MS` | no       | Screening request timeout in ms (default `90000`)             |

Give the **origin only** — scheme, host and port. No trailing slash and no `/api/v1`
suffix: the app appends `/api/v1/screen` itself and normalises slashes, so a double
`//` can never occur.

If the variable is missing, blank or lacks an `http(s)://` scheme, the app treats
itself as unconfigured: the Review screen explains the problem and disables the submit
button. It never falls back to a guessed or hard-coded host.

> `EXPO_PUBLIC_*` values are inlined into the JS bundle at build time, so they are not
> secret. Only non-sensitive configuration belongs here — never API keys or tokens.
> **Restart the Expo dev server after changing `.env`.**

### Pointing at a locally running backend

The backend currently runs only on a developer machine (typically
`uvicorn ... --port 8000`). Which address works depends on where the app is running:

| Running the app on…       | Use                                        | Why                                                       |
| ------------------------- | ------------------------------------------ | --------------------------------------------------------- |
| Web browser / iOS sim     | `http://localhost:8000`                    | Shares the host's network namespace                        |
| Android emulator (AVD)    | `http://10.0.2.2:8000`                     | `10.0.2.2` is the emulator's alias for the host machine    |
| Physical phone over Wi-Fi | `http://<your-computer-LAN-IP>:8000`       | See the note below                                        |

**A physical phone cannot use `http://localhost:8000`.** On the phone, `localhost`
resolves to the phone itself, so the request never leaves the device and fails as a
connection error. Use the computer's LAN IP instead — find it with `ipconfig`
(Windows) or `ip addr` / `ifconfig` (macOS/Linux); it usually looks like
`192.168.x.x`. Both devices must be on the same network, the backend must bind
`0.0.0.0` (not `127.0.0.1`) so it accepts non-local connections, and the host
firewall must allow inbound traffic on the port.

When a deployed backend exists, set `EXPO_PUBLIC_API_BASE_URL` to its `https://` origin
— no code changes are required.

Useful scripts:

| Script              | Purpose                          |
| ------------------- | -------------------------------- |
| `npm start`         | Start the Expo dev server        |
| `npm run android`   | Launch on an Android device/emulator |
| `npm run typecheck` | TypeScript check (`tsc --noEmit`) |
| `npm run web`       | Run in a browser (useful for quick API checks) |

## Project structure

```
app/
├── App.tsx                  # Root: providers + navigator
├── .env.example             # Configuration template (copy to .env)
├── src/
│   ├── api/                 # Screening API client (fetch + multipart upload)
│   ├── components/          # Design-system primitives (Button, Card, Text, …)
│   ├── config/              # Env-driven API base URL + URL building
│   ├── constants/           # Product copy and capture-step metadata
│   ├── context/             # In-memory capture state + screening request state
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

## Submission & error handling

Submitting from Review issues one real `POST /api/v1/screen` multipart upload. The
request is owned by `ScreeningProvider` (`src/context/ScreeningContext.tsx`) rather
than by a screen, which means:

- Navigating Review → Processing cannot cancel it or lose the response.
- Duplicate submissions are blocked while a request is in flight.
- Processing only *reacts* to the outcome: it replaces itself with Result on success,
  or returns to Review on failure.
- A failure keeps the three captured images, so **retry never forces a recapture**.
- Cancelling aborts the request via `AbortController`; unmounting does the same.

Every failure mode is normalised into a single `ApiError`
(`src/api/errors.ts`) carrying user-facing copy, a `kind`, and a `retryable` flag:
missing configuration, missing captures, offline/unreachable host, timeout,
cancellation, HTTP 400/413/415/422/429/5xx, and non-JSON or unexpected response
bodies. Technical detail stays in the dev console; the UI shows the plain-language
message only, never a stack trace.

A successful response is structurally normalised in `src/api/screening.ts` but the
`status` string is passed through untouched, so a status this app version does not
know about renders as the safe "needs review" state instead of crashing or being
read as a pass.

### No mock data

There is no offline, demo or sample-response path anywhere in the app. If the backend
is unreachable, the app shows a real error. Results shown on the Result screen always
come from an actual backend response.

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
