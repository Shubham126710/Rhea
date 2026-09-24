import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";

/**
 * The one canonical implementation of the header's Theme/Notifications/
 * More controls, shared by Workspace, Search, and Settings -- replacing
 * three separately-disabled copies of the same buttons. Each control is
 * genuinely functional; none of them fabricate data.
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      className="text-on-surface-variant hover:text-on-surface transition-colors p-2"
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      type="button"
      onClick={toggleTheme}
    >
      <span className="material-symbols-outlined">{theme === "dark" ? "light_mode" : "dark_mode"}</span>
    </button>
  );
}

export function NotificationsControl() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        className="text-on-surface-variant hover:text-on-surface transition-colors p-2"
        title="Notifications"
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="material-symbols-outlined">notifications</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-surface-container-lowest border border-outline-variant rounded shadow-sm z-50 p-4">
          <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-2">
            Notifications
          </p>
          {/* No notification system exists on the backend yet -- an
              honest empty state, not a fabricated notification. */}
          <p className="font-body-md text-body-md text-on-surface-variant">No new notifications</p>
        </div>
      )}
    </div>
  );
}

export function MoreControl() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  async function handleLogout() {
    setOpen(false);
    await logout();
    sessionStorage.setItem("propagate:justLoggedOut", "1");
    window.location.assign("/login");
  }

  return (
    <div className="relative" ref={ref}>
      <button
        className="text-on-surface-variant hover:text-on-surface transition-colors p-2"
        title="More"
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="material-symbols-outlined">more_vert</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-56 bg-surface-container-lowest border border-outline-variant rounded shadow-sm z-50 py-2">
          <button
            className="w-full text-left px-4 py-2 font-body-md text-body-md text-on-surface hover:bg-surface-container transition-colors flex items-center gap-2"
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/settings");
            }}
          >
            <span className="material-symbols-outlined text-[18px]">settings</span>
            Settings
          </button>
          <button
            className="w-full text-left px-4 py-2 font-body-md text-body-md text-on-surface hover:bg-surface-container transition-colors flex items-center gap-2"
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/search");
            }}
          >
            <span className="material-symbols-outlined text-[18px]">history</span>
            History
          </button>
          <div className="border-t border-outline-variant my-1" />
          <button
            className="w-full text-left px-4 py-2 font-body-md text-body-md text-error hover:bg-surface-container transition-colors flex items-center gap-2"
            type="button"
            onClick={handleLogout}
          >
            <span className="material-symbols-outlined text-[18px]">logout</span>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
