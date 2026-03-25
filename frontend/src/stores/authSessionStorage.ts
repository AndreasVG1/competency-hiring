import type { AuthenticatedUser } from "../types/auth";

const SESSION_STORAGE_KEY = "competency_hiring.auth.session.v1";

interface PersistedAuthSession {
  accessToken: string;
  currentUser: AuthenticatedUser;
}

export function saveAuthSession(session: PersistedAuthSession): void {
  sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession(): void {
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
}

export function readAuthSession(): PersistedAuthSession | null {
  const rawValue = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as PersistedAuthSession;
    if (!parsed.accessToken || !parsed.currentUser) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
