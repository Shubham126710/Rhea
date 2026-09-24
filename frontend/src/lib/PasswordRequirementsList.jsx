import { getPasswordRequirements } from "./passwordRules.js";

/** Live, per-keystroke password requirement checklist. */
export function PasswordRequirementsList({ password }) {
  return (
    <ul className="mt-2 space-y-1 font-code-sm text-[12px]" aria-live="polite">
      {getPasswordRequirements(password).map((req) => (
        <li
          key={req.id}
          className={`flex items-center gap-2 transition-colors ${req.met ? "text-primary" : "text-on-surface-variant"}`}
        >
          <span className="material-symbols-outlined text-sm" aria-hidden="true">
            {req.met ? "check_circle" : "radio_button_unchecked"}
          </span>
          <span>{req.label}</span>
        </li>
      ))}
    </ul>
  );
}

/** Live password-match indicator, shared the same way. */
export function PasswordMatchNote({ password, confirm }) {
  if (confirm.length === 0) return null;
  const matches = password === confirm;
  return (
    <p className={`mt-1 font-code-sm text-[12px] ${matches ? "text-primary" : "text-error"}`} aria-live="polite">
      {matches ? "Passwords match." : "Passwords do not match."}
    </p>
  );
}

/** Reusable show/hide toggle button for a password field. */
export function PasswordVisibilityToggle({ visible, onToggle }) {
  return (
    <button
      aria-label={visible ? "Hide password" : "Show password"}
      aria-pressed={visible}
      className="absolute right-0 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface"
      type="button"
      onClick={onToggle}
    >
      <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
        {visible ? "visibility_off" : "visibility"}
      </span>
    </button>
  );
}
