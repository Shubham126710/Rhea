/**
 * Real Rhea API client.
 *
 * Every shape here is taken directly from the backend source of truth:
 *   - app/auth/schemas.py               (SignupRequest, LoginRequest, UserPublic, ...)
 *   - app/api/v1/auth.py                (routes + cookie-session behavior)
 *   - app/analysis_orchestration/schemas.py (Submit/Status/Result/History/Search)
 *   - app/api/v1/analyses.py, history.py, search.py, admin.py, research.py
 *
 * Sessions are cookie-based (HttpOnly, Secure, SameSite=lax) — the frontend
 * never stores a token itself. Every request therefore uses
 * `credentials: "include"`, and the API base must be an origin the backend's
 * CORS_ALLOWED_ORIGINS list actually contains (see .env / core/config.py).
 */

// Configure at deploy time: window.__PROPAGATE_API_BASE__ = "https://api.example.com"
// set from a small inline <script> in each page's <head>, or fall back to same-origin
// dev default matching backend/.env.example's implied local port.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, message, retryAfterSeconds) {
    super(message);
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

async function parseErrorAndThrow(response) {
  let detail = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // no JSON body
  }
  const retryAfterHeader = response.headers.get("Retry-After");
  throw new ApiError(
    response.status,
    detail,
    retryAfterHeader ? Number(retryAfterHeader) : undefined,
  );
}

async function requestJson(path, init) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: { "Content-Type": "application/json", ...(init && init.headers) },
  });
  if (!response.ok) return parseErrorAndThrow(response);
  if (response.status === 204) return null;
  return response.json();
}

// ---------------------------------------------------------------- health --
export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  if (!response.ok) throw new ApiError(response.status, `Health check failed: ${response.status}`);
  return response.json();
}

// ------------------------------------------------------------------ auth --
// POST /api/v1/auth/signup  -> { message }  (201; enumeration-safe: same
// message whether or not the email already existed. NOTE: the real backend
// has no email-verification step — an account is usable immediately after
// signup. There is no corresponding endpoint for the Stitch "verify email"
// screen; do not call one.)
export function signup({ email, display_name, password }) {
  return requestJson("/api/v1/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, display_name, password }),
  });
}

// POST /api/v1/auth/login -> UserPublic; sets the session cookie itself.
export function login({ email, password, remember_device = false }) {
  return requestJson("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, remember_device }),
  });
}

export function logout() {
  return requestJson("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({}) });
}

// GET /api/v1/auth/me -> UserPublic | null (401 means "not logged in", not an error)
export async function fetchCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) return parseErrorAndThrow(response);
  return response.json();
}

export function requestPasswordReset(email) {
  return requestJson("/api/v1/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(token, new_password) {
  return requestJson("/api/v1/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, new_password }),
  });
}

export function deleteAccount() {
  return requestJson("/api/v1/auth/me", { method: "DELETE" });
}

// -------------------------------------------------------------- analyses --
// POST /api/v1/analyses -> SubmitAnalysisResponse { analysis_reference_id, status }
export function submitText(text) {
  return requestJson("/api/v1/analyses", {
    method: "POST",
    body: JSON.stringify({ input_type: "text", text }),
  });
}

export function submitUrl(url) {
  return requestJson("/api/v1/analyses", {
    method: "POST",
    body: JSON.stringify({ input_type: "url", url }),
  });
}

// POST /api/v1/analyses/upload (multipart) -> SubmitAnalysisResponse
export async function submitFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/v1/analyses/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!response.ok) return parseErrorAndThrow(response);
  return response.json();
}

// GET /api/v1/analyses/{id}/status -> { status: pending|processing|complete|failed, stage }
export function getStatus(referenceId) {
  return requestJson(`/api/v1/analyses/${referenceId}/status`);
}

// GET /api/v1/analyses/{id} -> AnalysisResultResponse (verdict, graph, evidence, ...)
export function getResult(referenceId) {
  return requestJson(`/api/v1/analyses/${referenceId}`);
}

// DELETE /api/v1/analyses/{id} -> cancel (only valid while not yet complete/failed)
export function cancelAnalysis(referenceId) {
  return requestJson(`/api/v1/analyses/${referenceId}`, { method: "DELETE" });
}

// POST /api/v1/analyses/{id}/explanation/retry
export function retryExplanation(referenceId) {
  return requestJson(`/api/v1/analyses/${referenceId}/explanation/retry`, { method: "POST" });
}

// ---------------------------------------------------------------- history --
export function getHistory(limit = 20, offset = 0) {
  return requestJson(`/api/v1/history?limit=${limit}&offset=${offset}`);
}

// ----------------------------------------------------------------- search --
export function search(query) {
  return requestJson(`/api/v1/search?q=${encodeURIComponent(query)}`);
}

// ------------------------------------------------------------------ admin --
// RBAC-gated (admin/research role only) — call only after auth/me confirms role.
export function getModelStatus() {
  return requestJson("/api/v1/admin/model-status");
}

export function getEvaluationSummary() {
  return requestJson("/api/v1/research/evaluation-summary");
}

// ------------------------------------------------------------- utilities --
export function pollStatus(referenceId, { intervalMs = 1500, onUpdate, signal } = {}) {
  return new Promise((resolve, reject) => {
    let stopped = false;
    if (signal) signal.addEventListener("abort", () => { stopped = true; });

    async function tick() {
      if (stopped) return;
      try {
        const status = await getStatus(referenceId);
        if (onUpdate) onUpdate(status);
        if (status.status === "complete" || status.status === "failed") {
          resolve(status);
          return;
        }
      } catch (err) {
        reject(err);
        return;
      }
      if (!stopped) setTimeout(tick, intervalMs);
    }
    tick();
  });
}
