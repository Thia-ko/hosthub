"use client";

import { useSyncExternalStore } from "react";

function subscribeNever() {
  return () => {};
}

/**
 * True only once the component has hydrated on the client. Lets client-only UI (theme toggle,
 * browser APIs, localStorage-backed state) skip rendering during SSR without a `useEffect` +
 * `setState` mount flag - see https://react.dev/reference/react/useSyncExternalStore.
 */
export function useIsClient(): boolean {
  return useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );
}
