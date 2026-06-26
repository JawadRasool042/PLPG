export const ADMIN_REALTIME_POLL_MS = 5000;

export const adminRealtimeQueryOptions = {
  refetchInterval: ADMIN_REALTIME_POLL_MS,
  refetchIntervalInBackground: true,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
  staleTime: 0,
} as const;

