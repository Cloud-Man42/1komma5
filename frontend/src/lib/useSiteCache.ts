import { useCallback, useEffect, useRef, useState } from "react";

interface CacheEntry<T> {
  value: T;
  fetchedAt: number;
}

const cache = new Map<string, CacheEntry<unknown>>();

export function useSiteCache<T>(
  key: string,
  loader: () => Promise<T>,
  ttlMs: number,
): { data: T | null; loading: boolean; error: string | null; reload: () => Promise<void> } {
  const [data, setData] = useState<T | null>(() => {
    const hit = cache.get(key) as CacheEntry<T> | undefined;
    if (hit && Date.now() - hit.fetchedAt < ttlMs) return hit.value;
    return null;
  });
  const [loading, setLoading] = useState(data === null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const load = useCallback(async () => {
    const hit = cache.get(key) as CacheEntry<T> | undefined;
    if (hit && Date.now() - hit.fetchedAt < ttlMs) {
      setData(hit.value);
      setLoading(false);
      return;
    }
    try {
      const value = await loader();
      if (!mounted.current) return;
      cache.set(key, { value, fetchedAt: Date.now() });
      setData(value);
      setError(null);
    } catch (e) {
      if (!mounted.current) return;
      setError(e instanceof Error ? e.message : "Kunde inte ladda data");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [key, loader, ttlMs]);

  useEffect(() => {
    mounted.current = true;
    void load();
    return () => {
      mounted.current = false;
    };
  }, [load]);

  return { data, loading, error, reload: load };
}

export function clearSiteCache(prefix: string) {
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) cache.delete(key);
  }
}
