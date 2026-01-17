/**
 * Patient portal authentication utilities.
 * Uses a distinct localStorage key to avoid conflicts with staff portal.
 */

export const AUTH_TOKEN_KEY = 'patient_access_token';

export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
};

export const setToken = (token: string): void => {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
};

export const removeToken = (): void => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
};
