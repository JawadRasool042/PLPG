export interface FriendlyApiError {
  message: string;
  code?: string;
  status?: number;
}

/**
 * Normalize Flask / plain-fetch JSON error bodies into one user-visible string.
 * Handles `detail` (string or list), `message`, `error`, and `errors` (field list).
 */
export function messageFromApiJsonBody(
  data: Record<string, unknown> | null | undefined,
  fallback: string
): string {
  if (!data || typeof data !== 'object') return fallback;

  const detail = data.detail;
  if (typeof detail === 'string' && detail.trim()) {
    let out = detail.trim();
    if (typeof data.hint === 'string' && data.hint.trim()) {
      out += ` ${data.hint.trim()}`;
    }
    return out;
  }
  if (Array.isArray(detail)) {
    const parts = detail.map((item: unknown) => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object') {
        const o = item as Record<string, unknown>;
        if (typeof o.msg === 'string') return o.msg;
        if (typeof o.message === 'string') return o.message;
      }
      return '';
    });
    const joined = parts.filter(Boolean).join('; ');
    if (joined) return joined;
  }

  if (typeof data.message === 'string' && data.message.trim()) return data.message.trim();
  if (typeof data.error === 'string' && data.error.trim()) return data.error.trim();

  const errors = data.errors;
  if (Array.isArray(errors)) {
    const msgs = errors
      .map((e: unknown) => {
        if (e && typeof e === 'object' && typeof (e as Record<string, unknown>).message === 'string') {
          return (e as Record<string, unknown>).message as string;
        }
        return '';
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }

  return fallback;
}

const AUTH_ERROR_CODES = new Set([
  'NO_TOKEN',
  'INVALID_TOKEN',
  'INVALID_HEADER',
  'TOKEN_EXPIRED',
  'PASSWORD_CHANGED',
  'UNAUTHORIZED',
  'INVALID_TOKEN_CONTEXT',
]);

export const parseApiError = (error: unknown, fallback: string): FriendlyApiError => {
  const err = error as any;
  const data = err?.response?.data || err?.data || {};
  const status = err?.response?.status || err?.status;
  const code = data?.error_code || data?.code || err?.code;
  const rawMessage =
    data?.detail ||
    data?.message ||
    data?.error ||
    err?.message ||
    fallback;

  if (status === 401 || (typeof code === 'string' && AUTH_ERROR_CODES.has(code))) {
    if (code === 'INVALID_TOKEN_CONTEXT') {
      return {
        message:
          rawMessage ||
          'Your login session could not be verified (invalid or outdated token). Please sign out and log in again.',
        code,
        status,
      };
    }
    if (code === 'NO_TOKEN') {
      return {
        message: rawMessage || 'No access token was sent. Add Authorization: Bearer <token> or log in again.',
        code,
        status,
      };
    }
    if (code === 'INVALID_HEADER') {
      return {
        message:
          rawMessage ||
          'Authorization header must be exactly: Bearer <access_token> (two parts, Bearer + token).',
        code,
        status,
      };
    }
    if (code === 'INVALID_TOKEN') {
      return {
        message:
          rawMessage ||
          'Token is invalid (wrong signature, malformed JWT, or not an access token). Request a new token by logging in again.',
        code,
        status,
      };
    }
    if (code === 'TOKEN_EXPIRED') {
      return { message: rawMessage || 'Your session expired. Please log in again.', code, status };
    }
    if (code === 'PASSWORD_CHANGED') {
      return { message: rawMessage || 'Your password changed recently. Please log in again.', code, status };
    }
    if (code === 'USER_NOT_FOUND') {
      return { message: rawMessage || 'User account no longer exists.', code, status };
    }
    return {
      message: rawMessage || 'Authentication failed. Please log in again.',
      code,
      status,
    };
  }

  if (status === 403 && code === 'ACCOUNT_INACTIVE') {
    return {
      message: rawMessage || 'This account is deactivated.',
      code,
      status,
    };
  }

  if (status === 403) {
    return {
      message: rawMessage || 'You do not have permission to perform this action.',
      code,
      status,
    };
  }

  return {
    message: rawMessage || fallback,
    code,
    status,
  };
};

/**
 * Re-throw using {@link parseApiError} but attach `code` and `status` on the Error so
 * callers can detect auth failures (e.g. redirect to login) after `Promise.allSettled`.
 */
export function throwParsedApiError(error: unknown, fallback: string): never {
  const p = parseApiError(error, fallback);
  throw Object.assign(new Error(p.message), { code: p.code, status: p.status });
}

