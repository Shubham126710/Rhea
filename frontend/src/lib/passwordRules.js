/**
 * Password policy enforced by the frontend UI.
 *
 * NOTE on the backend contract: the real backend's own validation is
 * only `Field(min_length=8, max_length=200)` (see app/auth/schemas.py) --
 * it does not itself check for character classes. The five rules below
 * are a deliberate, explicitly-requested frontend-side policy that is
 * *stricter* than what the backend requires. That's safe (a client can
 * always require more than the server does, never less) and is not
 * "frontend-only validation replacing backend validation" -- the
 * backend still independently enforces its own 8-200 length rule
 * regardless of what the client sends. This module is shared by the
 * sign-up and reset-password pages so both show and enforce identical
 * rules.
 */
export function getPasswordRequirements(password) {
  return [
    { id: "min-length", label: "At least 8 characters", met: password.length >= 8 },
    { id: "lowercase", label: "At least 1 lowercase letter", met: /[a-z]/.test(password) },
    { id: "uppercase", label: "At least 1 uppercase letter", met: /[A-Z]/.test(password) },
    { id: "digit", label: "At least 1 number", met: /[0-9]/.test(password) },
    {
      id: "special",
      label: "At least 1 special character",
      met: /[^A-Za-z0-9]/.test(password),
    },
  ];
}

export function isPasswordValid(password) {
  return getPasswordRequirements(password).every((r) => r.met);
}

/**
 * Renders/updates a live checklist inside `listEl` (a <ul> or <ol>).
 * Called on every keystroke -- each requirement's icon/color flips
 * immediately as it becomes satisfied or not, per the requirement
 * for live, per-keystroke feedback.
 */
export function renderPasswordChecklist(listEl, password) {
  listEl.innerHTML = "";
  for (const req of getPasswordRequirements(password)) {
    const li = document.createElement("li");
    li.className = `flex items-center gap-2 transition-colors ${req.met ? "text-primary" : "text-on-surface-variant"}`;
    li.id = `pw-req-${req.id}`;
    li.innerHTML = `<span class="material-symbols-outlined text-sm" aria-hidden="true">${req.met ? "check_circle" : "radio_button_unchecked"}</span><span>${req.label}</span>`;
    listEl.appendChild(li);
  }
}

/** Wires a password <input> + visibility-toggle <button> pair. */
export function wirePasswordVisibilityToggle(inputEl, toggleBtnEl) {
  toggleBtnEl.addEventListener("click", () => {
    const showing = inputEl.type === "text";
    inputEl.type = showing ? "password" : "text";
    toggleBtnEl.setAttribute("aria-pressed", String(!showing));
    toggleBtnEl.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    toggleBtnEl.querySelector(".material-symbols-outlined").textContent = showing
      ? "visibility"
      : "visibility_off";
  });
}
