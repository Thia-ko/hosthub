"use client";

import { useCallback, useEffect, useState } from "react";
import { GENERIC_LOAD_ERROR_MESSAGE, errorMessage } from "@/lib/api-client";

interface AsyncDataState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/**
 * Fetches on mount and whenever `deps` changes; tracks loading/error and exposes a manual
 * `reload`. Centralizes the fetch/loading/error triplet repeated across every list/detail page.
 */
export function useAsyncData<T>(fetcher: () => Promise<T>, deps: unknown[]): AsyncDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const depsKey = JSON.stringify(deps);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch((err: unknown) => {
        setError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE));
      })
      .finally(() => setLoading(false));
    // depsKey mirrors `deps` for change detection (fetcher is a fresh closure every render,
    // intentionally excluded so it doesn't force a re-fetch on every parent re-render).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depsKey, tick]);

  useEffect(() => {
    // Fetching on mount is a necessary Effect (react.dev/learn/you-might-not-need-an-effect
    // #fetching-data); `load` resets loading/error synchronously before the fetch settles,
    // which set-state-in-effect can't distinguish from a derived-state anti-pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return { data, error, loading, reload: () => setTick((current) => current + 1) };
}
