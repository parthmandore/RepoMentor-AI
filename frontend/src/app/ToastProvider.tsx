'use client';

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextType {
  toast: {
    success: (message: string, duration?: number) => void;
    error: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
    info: (message: string, duration?: number) => void;
    dismiss: (id: string) => void;
  };
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const dismiss = useCallback((id: string) => {
    // Clear timer
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((type: ToastType, message: string, duration = 4500) => {
    setToasts((prev) => {
      // Deduplicate: if a toast with the exact message is already active, don't duplicate
      const existing = prev.find((t) => t.message === message && t.type === type);
      if (existing) {
        // Reset its timer
        const timer = timersRef.current.get(existing.id);
        if (timer) clearTimeout(timer);
        timersRef.current.set(
          existing.id,
          setTimeout(() => dismiss(existing.id), duration)
        );
        return prev;
      }

      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      timersRef.current.set(
        id,
        setTimeout(() => dismiss(id), duration)
      );
      return [...prev, { id, type, message, duration }];
    });
  }, [dismiss]);

  const toast = {
    success: (msg: string, d?: number) => addToast('success', msg, d),
    error: (msg: string, d?: number) => addToast('error', msg, d),
    warning: (msg: string, d?: number) => addToast('warning', msg, d),
    info: (msg: string, d?: number) => addToast('info', msg, d),
    dismiss,
  };

  const getToastStyles = (type: ToastType) => {
    switch (type) {
      case 'success':
        return {
          icon: <CheckCircle2 className="w-4 h-4 text-good shrink-0 mt-0.5" />,
          container: 'bg-bgSecondary border-good-border text-textPrimary shadow-report',
        };
      case 'error':
        return {
          icon: <AlertCircle className="w-4 h-4 text-bad shrink-0 mt-0.5" />,
          container: 'bg-bgSecondary border-bad-border text-textPrimary shadow-report',
        };
      case 'warning':
        return {
          icon: <AlertTriangle className="w-4 h-4 text-warn shrink-0 mt-0.5" />,
          container: 'bg-bgSecondary border-warn-border text-textPrimary shadow-report',
        };
      case 'info':
      default:
        return {
          icon: <Info className="w-4 h-4 text-signal shrink-0 mt-0.5" />,
          container: 'bg-bgSecondary border-borderPrimary text-textPrimary shadow-report',
        };
    }
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Accessible Toast Notification Region */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none"
      >
        {toasts.map((item) => {
          const style = getToastStyles(item.type);
          return (
            <div
              key={item.id}
              role="status"
              className={`pointer-events-auto p-3.5 rounded-2xl border shadow-lg backdrop-blur-md flex items-start justify-between gap-3 transition-all duration-300 animate-slide-in-right ${style.container}`}
              onMouseEnter={() => {
                const timer = timersRef.current.get(item.id);
                if (timer) clearTimeout(timer);
              }}
              onMouseLeave={() => {
                timersRef.current.set(
                  item.id,
                  setTimeout(() => dismiss(item.id), item.duration || 4500)
                );
              }}
            >
              <div className="flex items-start gap-2.5 min-w-0">
                {style.icon}
                <p className="text-xs font-medium leading-relaxed break-words">{item.message}</p>
              </div>
              <button
                onClick={() => dismiss(item.id)}
                aria-label="Dismiss notification"
                className="p-1 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 opacity-70 hover:opacity-100 transition-opacity focus:outline-none focus-visible:ring-1 focus-visible:ring-current shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context.toast;
}
