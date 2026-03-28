"use client";

import { createContext, useContext, useState, useCallback, useRef } from "react";

interface ToastItem {
  id: number;
  message: string;
  type: "success" | "info";
}

const ToastContext = createContext<(message: string, type?: "success" | "info") => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const show = useCallback((message: string, type: "success" | "info" = "success") => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 2800);
  }, []);

  return (
    <ToastContext value={show}>
      {children}
      <div
        style={{
          position: "fixed",
          top: 80,
          right: 24,
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          pointerEvents: "none",
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="toast-enter"
            style={{
              padding: "10px 20px",
              borderRadius: "var(--radius-md)",
              background:
                t.type === "success"
                  ? "var(--color-primary)"
                  : "var(--color-surface-container-lowest)",
              color:
                t.type === "success"
                  ? "var(--color-on-primary)"
                  : "var(--color-text-primary)",
              boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
              fontSize: 13,
              fontWeight: 600,
              maxWidth: 360,
              pointerEvents: "auto",
            }}
          >
            {t.type === "success" && (
              <span style={{ marginRight: 6 }}>OK</span>
            )}
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext>
  );
}
