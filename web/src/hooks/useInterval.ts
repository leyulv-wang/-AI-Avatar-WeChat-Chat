import { useEffect, useRef } from "react";

export function useInterval(fn: () => void, delayMs: number | null) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (delayMs === null) return;
    const id = window.setInterval(() => fnRef.current(), delayMs);
    return () => window.clearInterval(id);
  }, [delayMs]);
}

