import { createContext, useCallback, useContext, useRef, useState } from "react";

const ToastContext = createContext(null);

const VARIANT_CLASS = {
  success: "border-primary text-primary",
  error: "border-error text-error",
  info: "border-outline-variant text-on-surface-variant",
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message, variant = "info", { durationMs = 5000 } = {}) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, message, variant }]);
      if (durationMs > 0) {
        setTimeout(() => dismiss(id), durationMs);
      }
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        style={{
          position: "fixed",
          bottom: "1rem",
          right: "1rem",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          maxWidth: "24rem",
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.variant === "error" ? "alert" : "status"}
            className={`bg-surface-container-lowest border shadow-sm rounded px-4 py-3 font-body-md text-body-md text-on-surface flex items-start gap-3 ${VARIANT_CLASS[t.variant] ?? VARIANT_CLASS.info}`}
          >
            <span className="flex-1">{t.message}</span>
            <button
              type="button"
              aria-label="Dismiss notification"
              className="text-on-surface-variant hover:text-on-surface shrink-0"
              onClick={() => dismiss(t.id)}
            >
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Returns a `showToast(message, variant, opts)` function. */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
