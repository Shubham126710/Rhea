import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { requestPasswordReset, confirmPasswordReset, ApiError } from "../api/client.js";
import { isPasswordValid } from "../lib/passwordRules.js";
import {
  PasswordRequirementsList,
  PasswordMatchNote,
  PasswordVisibilityToggle,
} from "../lib/PasswordRequirementsList.jsx";
import { useToast } from "../lib/toast.jsx";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();
  const showToast = useToast();

  // "request" (no token -- real default) | "active" | "success" | "error"
  const [view, setView] = useState(token ? "active" : "request");
  const [errorDetail, setErrorDetail] = useState(
    "This password reset link has expired or is no longer valid. Please request a new link to reset your password.",
  );

  return (
    <div className="bg-[#0C0C0C] min-h-screen flex flex-col font-sans text-base text-[#F3F3F2] selection:bg-[#F3F3F2] selection:text-[#0C0C0C] relative">
      {/* Grain Overlay */}
      <div className="pointer-events-none absolute inset-0 bg-grain z-50 mix-blend-overlay"></div>

      <header className="w-full flex items-center justify-center p-8 bg-transparent fixed top-0 z-40">
        <div className="flex items-center gap-2">
          <span className="font-body-md text-3xl tracking-widest text-[#F3F3F2]">
            RH<span className="italic">E</span>A
          </span>
        </div>
      </header>
      <main className="flex-grow flex items-center justify-center p-6 mt-16 relative overflow-hidden z-10">
        <div className="w-full max-w-md bg-black/40 border border-white/10 backdrop-blur-md shadow-sm rounded-xl flex flex-col relative z-10">
          {view === "request" && <RequestView showToast={showToast} />}
          {view === "active" && (
            <ActiveView
              token={token}
              showToast={showToast}
              onSuccess={() => setView("success")}
              onInvalidToken={(message) => {
                setErrorDetail(message);
                setView("error");
              }}
            />
          )}
          {view === "success" && <SuccessView navigate={navigate} />}
          {view === "error" && <ErrorView detail={errorDetail} navigate={navigate} />}
        </div>
      </main>
    </div>
  );
}

function RequestView({ showToast }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    setError("");
    setSuccess("");
    setSubmitting(true);
    try {
      const { message } = await requestPasswordReset(email.trim());
      // Honest about local dev: the real backend's only implemented email
      // sender in development prints the reset link to the backend
      // console rather than sending a real email (see
      // app/auth/email.py::ConsoleDevEmailSender). Say so plainly instead
      // of implying an email definitely arrived.
      setSuccess(
        `${message} If you're running this locally, no real email is sent \u2014 check the backend server's console output for the reset link.`,
      );
      showToast("Reset request submitted.", "success");
      setEmail("");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not reach the server.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-10 flex flex-col gap-8">
      <div className="text-center">
        <h1 className="text-3xl font-body-md font-light text-white mb-2">Reset Password</h1>
        <p className="text-sm text-white/50 font-light">
          Enter your account email and we'll send a link to reset your password.
        </p>
      </div>
      <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
        {error && (
          <p className="text-sm text-red-400" role="alert">
            {error}
          </p>
        )}
        {success && (
          <p className="text-sm text-[#F3F3F2]" role="status">
            {success}
          </p>
        )}
        <div className="flex flex-col gap-2 group">
          <label className="text-[11px] uppercase tracking-widest text-white/50 group-focus-within:text-white/80 transition-colors" htmlFor="request-email">
            Email
          </label>
          <input
            className="w-full bg-transparent border-0 border-b border-white/20 focus:border-white focus:ring-0 text-base py-2 px-0 text-white placeholder:text-white/20 transition-colors"
            id="request-email"
            placeholder="jane@example.com"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <button
          className="w-full bg-[#F3F3F2] hover:bg-white text-[#0C0C0C] text-xs tracking-wider uppercase font-medium py-4 rounded-sm transition-colors flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          type="submit"
          disabled={submitting}
        >
          {submitting && (
            <span className="material-symbols-outlined text-[16px] animate-spin" aria-hidden="true">
              progress_activity
            </span>
          )}
          <span>{submitting ? "Sending..." : "Send Reset Link"}</span>
        </button>
        <a
          className="w-full bg-transparent border border-white/20 text-white hover:bg-white/5 text-xs tracking-wider uppercase font-medium py-4 rounded-sm transition-colors flex justify-center items-center gap-2"
          href="/login"
        >
          Back to Login
        </a>
      </form>
    </div>
  );
}

function ActiveView({ token, showToast, onSuccess, onInvalidToken }) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const ready = isPasswordValid(newPassword) && newPassword === confirmPassword && confirmPassword.length > 0;

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting || !ready) return;
    setError("");
    setSubmitting(true);
    try {
      await confirmPasswordReset(token, newPassword);
      showToast("Password updated.", "success");
      onSuccess();
    } catch (err) {
      // The real backend returns 400 specifically for an invalid/expired
      // token (InvalidOrExpiredToken) -- that, and only that, is what
      // triggers the "Link Expired" state. Any other failure is a normal
      // inline form error, not a fabricated "expired" message.
      if (err instanceof ApiError && err.status === 400) {
        onInvalidToken(err.message);
        return;
      }
      const msg = err instanceof ApiError ? err.message : "Could not reach the server.";
      setError(msg);
      showToast(msg, "error");
      setSubmitting(false);
    }
  }

  return (
    <div className="p-10 flex flex-col gap-8">
      <div className="text-center">
        <h1 className="text-3xl font-body-md font-light text-white mb-2">Reset Password</h1>
        <p className="text-sm text-white/50 font-light">
          Please enter a new, secure password for your Rhea account.
        </p>
      </div>
      <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
        {error && (
          <p className="text-sm text-red-400" role="alert">
            {error}
          </p>
        )}
        <div className="flex flex-col gap-2 group">
          <label className="text-[11px] uppercase tracking-widest text-white/50 group-focus-within:text-white/80 transition-colors" htmlFor="new-password">
            New Password
          </label>
          <div className="relative">
            <input
              className="w-full bg-transparent border-0 border-b border-white/20 focus:border-white focus:ring-0 text-base py-2 px-0 pr-8 text-white placeholder:text-white/20 transition-colors"
              id="new-password"
              placeholder="Enter new password"
              type={showNew ? "text" : "password"}
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => {
                setNewPassword(e.target.value);
                setError("");
              }}
            />
            <PasswordVisibilityToggle visible={showNew} onToggle={() => setShowNew((v) => !v)} />
          </div>
        </div>
        <div className="flex flex-col gap-2 group">
          <label className="text-[11px] uppercase tracking-widest text-white/50 group-focus-within:text-white/80 transition-colors" htmlFor="confirm-password">
            Confirm Password
          </label>
          <div className="relative">
            <input
              className="w-full bg-transparent border-0 border-b border-white/20 focus:border-white focus:ring-0 text-base py-2 px-0 pr-8 text-white placeholder:text-white/20 transition-colors"
              id="confirm-password"
              placeholder="Confirm new password"
              type={showConfirm ? "text" : "password"}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setError("");
              }}
            />
            <PasswordVisibilityToggle visible={showConfirm} onToggle={() => setShowConfirm((v) => !v)} />
          </div>
          <PasswordMatchNote password={newPassword} confirm={confirmPassword} />
        </div>
        <div className="bg-white/5 p-4 border border-white/10 rounded-sm mt-2">
          <p className="text-[11px] uppercase tracking-widest text-white/50 mb-3">Password Requirements:</p>
          <PasswordRequirementsList password={newPassword} />
        </div>
        <button
          className="w-full bg-[#F3F3F2] hover:bg-white text-[#0C0C0C] text-xs tracking-wider uppercase font-medium py-4 rounded-sm transition-colors mt-4 flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          type="submit"
          disabled={!ready || submitting}
        >
          {submitting && (
            <span className="material-symbols-outlined text-[16px] animate-spin" aria-hidden="true">
              progress_activity
            </span>
          )}
          <span>{submitting ? "Updating..." : "Update Password"}</span>
        </button>
        <a
          className="w-full bg-transparent border border-white/20 text-white hover:bg-white/5 text-xs tracking-wider uppercase font-medium py-4 rounded-sm transition-colors mt-2 flex justify-center items-center gap-2"
          href="/login"
        >
          Cancel
        </a>
      </form>
    </div>
  );
}

function SuccessView({ navigate }) {
  return (
    <div className="p-10 flex flex-col gap-6 items-center text-center">
      <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-4">
        <span className="material-symbols-outlined text-[#F3F3F2] text-3xl">check_circle</span>
      </div>
      <h2 className="text-3xl font-body-md font-light text-white">Password Reset Complete</h2>
      <p className="text-sm text-white/50 font-light">
        Your password has been successfully updated. You can now use your new password to log in to your Rhea
        account.
      </p>
      <button
        className="w-full bg-[#F3F3F2] hover:bg-white text-[#0C0C0C] text-xs tracking-wider uppercase font-medium py-4 rounded-sm transition-colors mt-6 flex justify-center items-center gap-2"
        type="button"
        onClick={() => navigate("/login")}
      >
        Return to Login
      </button>
    </div>
  );
}

function ErrorView({ detail, navigate }) {
  return (
    <div className="p-10 flex flex-col gap-6 items-center text-center">
      <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
        <span className="material-symbols-outlined text-red-400 text-3xl">error</span>
      </div>
      <h2 className="text-3xl font-body-md font-light text-white">Link Expired</h2>
      <p className="text-sm text-white/50 font-light">{detail}</p>
      <button
        className="w-full bg-transparent border border-white/20 text-white hover:bg-white/5 text-xs tracking-wider uppercase font-medium py-4 rounded-sm transition-colors mt-6 flex justify-center items-center gap-2"
        type="button"
        onClick={() => navigate("/login")}
      >
        Back to Login
      </button>
    </div>
  );
}
