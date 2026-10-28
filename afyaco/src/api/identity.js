import { session, BASE_URL, ApiError } from './client';

async function rawRequest(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    throw new ApiError(payload?.detail ? String(payload.detail) : `Request failed (${res.status})`, res.status, payload);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const identityApi = {
  // Enrollment — now a two-step challenge-response flow (see backend
  // app/services/liveness_challenge.py): the server picks a random action,
  // the client bursts frames while performing it, the server measures
  // whether the head actually moved before ever creating a template.
  beginEnrollmentChallenge: (memberId) =>
    rawRequest(`/api/v1/identity/enrollments/challenge?member_id=${memberId}`, { method: 'POST' }),
  createEnrollment: (memberId, livenessChallengeId, framesBase64, consentRef) =>
    rawRequest('/api/v1/identity/enrollments', {
      method: 'POST',
      body: {
        member_id: memberId,
        liveness_challenge_id: livenessChallengeId,
        frames_base64: framesBase64,
        consent_ref: consentRef,
      },
    }),
  getEnrollment: (memberId) => rawRequest(`/api/v1/identity/enrollments/${memberId}`),
  revokeEnrollment: (enrollmentId) => rawRequest(`/api/v1/identity/enrollments/${enrollmentId}/revoke`, { method: 'POST' }),

  createEncounter: (memberId, facilityProviderId, appointmentId = null) =>
    rawRequest('/api/v1/identity/encounters', {
      method: 'POST',
      body: { member_id: memberId, facility_provider_id: facilityProviderId, appointment_id: appointmentId },
    }),
  getEncounter: (encounterId) => rawRequest(`/api/v1/identity/encounters/${encounterId}`),
  getEncounterAttempt: (encounterId) => rawRequest(`/api/v1/identity/encounters/${encounterId}/attempt`),
  issueChallenge: (encounterId) => rawRequest(`/api/v1/identity/encounters/${encounterId}/challenge`, { method: 'POST' }),

  // Hospital-visit verification — also two-step: /start consumes the
  // facility's one-time QR and returns the random action to perform;
  // /complete submits the frame burst + location.
  startVerification: (challengeToken, facilityProviderId) =>
    rawRequest('/api/v1/identity/verify/start', {
      method: 'POST',
      body: { challenge_token: challengeToken, facility_provider_id: facilityProviderId },
    }),
  completeVerification: (livenessChallengeId, framesBase64, location) =>
    rawRequest('/api/v1/identity/verify/complete', {
      method: 'POST',
      body: { liveness_challenge_id: livenessChallengeId, frames_base64: framesBase64, location },
    }),
  retryVerification: (encounterId) =>
    rawRequest('/api/v1/identity/verify/retry', { method: 'POST', body: { encounter_id: encounterId } }),
};

// --- capture helpers -------------------------------------------------------

export function fileToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function frameToBase64(videoEl, quality = 0.85) {
  const canvas = document.createElement('canvas');
  canvas.width = videoEl.videoWidth;
  canvas.height = videoEl.videoHeight;
  canvas.getContext('2d').drawImage(videoEl, 0, 0);
  return new Promise((resolve) => {
    canvas.toBlob(async (blob) => resolve(await fileToBase64(blob)), 'image/jpeg', quality);
  });
}

export const captureFrameAsBase64 = frameToBase64;

// Captures frame[0] immediately (the "baseline" frontal shot), then keeps
// capturing every `intervalMs` for the rest of `totalMs` — the window during
// which the member performs the instructed head movement.
export async function captureChallengeBurst(videoEl, { totalMs = 2200, intervalMs = 250 } = {}) {
  const frames = [await frameToBase64(videoEl)];
  const steps = Math.floor(totalMs / intervalMs);
  for (let i = 0; i < steps; i++) {
    await new Promise((r) => setTimeout(r, intervalMs));
    frames.push(await frameToBase64(videoEl));
  }
  return frames;
}

export function getLocationSignal(timeoutMs = 8000) {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
          captured_at: new Date(pos.timestamp).toISOString(),
        }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 0 }
    );
  });
}
