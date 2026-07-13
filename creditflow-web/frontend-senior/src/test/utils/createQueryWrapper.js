import { createElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/**
 * Builds a fresh QueryClient (retries disabled so failures surface
 * immediately in tests) plus the wrapper component `renderHook` needs.
 * Written with createElement instead of JSX so this file stays plain .js
 * (no jsx loader configured for the test file glob).
 */
export function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  function wrapper({ children }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  }

  return { queryClient, wrapper };
}
