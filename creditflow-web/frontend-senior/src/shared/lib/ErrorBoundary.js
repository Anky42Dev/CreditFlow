"use client";

// DOC 6 §7.1: three-level Error Boundary hierarchy.
//   RootErrorBoundary   → fatal error anywhere in the app → full-page fallback
//   RouteErrorBoundary  → error inside a route segment    → local fallback + "back"
//   WidgetErrorBoundary  → error inside one widget         → isolates it, page stays alive
//
// All three are built on the same base class; only the fallback UI and the
// reported context differ.

import React from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { reportError } from "@/shared/lib/monitoring";

class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    reportError(error, {
      ...this.props.reportContext,
      componentStack: info?.componentStack,
    });
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return this.props.renderFallback
        ? this.props.renderFallback(this.state.error, this.reset)
        : this.props.fallback;
    }
    return this.props.children;
  }
}

export function RootErrorBoundary({ children }) {
  return (
    <ErrorBoundary
      reportContext={{ boundary: "root" }}
      fallback={
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
          <AlertTriangle size={40} className="text-red-500" />
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            Что-то пошло не так
          </h1>
          <p className="max-w-sm text-sm text-gray-500 dark:text-gray-400">
            Приложение столкнулось с непредвиденной ошибкой. Попробуйте
            обновить страницу.
          </p>
          <Button onClick={() => window.location.reload()}>
            <RefreshCw size={16} />
            Обновить страницу
          </Button>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

export function RouteErrorBoundary({ children }) {
  return (
    <ErrorBoundary
      reportContext={{ boundary: "route" }}
      renderFallback={(_error, reset) => (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <AlertTriangle size={32} className="text-red-500" />
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Не удалось загрузить страницу
          </p>
          <div className="flex gap-2">
            <Link href="/">
              <Button variant="secondary">Назад</Button>
            </Link>
            <Button onClick={reset}>Повторить</Button>
          </div>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

export function WidgetErrorBoundary({ children, name }) {
  return (
    <ErrorBoundary
      reportContext={{ boundary: "widget", widget: name }}
      renderFallback={(_error, reset) => (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-900 dark:bg-red-950/30">
          <AlertTriangle size={20} className="text-red-500" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Этот блок не удалось отобразить
          </p>
          <Button variant="secondary" onClick={reset} className="mt-1">
            Повторить
          </Button>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}
