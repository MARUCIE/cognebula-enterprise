"use client";

import { useToast } from "./Toast";

export function ToastButton({
  message,
  children,
  className,
  style,
  type = "success",
}: {
  message: string;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  type?: "success" | "info";
}) {
  const toast = useToast();
  return (
    <button className={className} style={style} onClick={() => toast(message, type)}>
      {children}
    </button>
  );
}
