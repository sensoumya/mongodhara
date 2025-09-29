import { writable } from 'svelte/store';

export interface ErrorOverlayState {
  visible: boolean;
  errorType: 'auth' | 'network' | 'server' | 'unknown';
  statusCode?: number;
  message?: string;
}

// Enhanced store to control overlay with error details
export const errorOverlayState = writable<ErrorOverlayState>({
  visible: false,
  errorType: 'unknown'
});

/**
 * Show the error overlay for authentication errors (401/403)
 */
export function triggerAuthError(status: number, message?: string) {
  errorOverlayState.set({
    visible: true,
    errorType: 'auth',
    statusCode: status,
    message: message || 'Authentication failed'
  });
}

/**
 * Show the error overlay for network errors
 */
export function triggerNetworkError(message?: string) {
  errorOverlayState.set({
    visible: true,
    errorType: 'network',
    message
  });
}

/**
 * Show the error overlay for server errors (5xx)
 */
export function triggerServerError(statusCode: number, message?: string) {
  errorOverlayState.set({
    visible: true,
    errorType: 'server',
    statusCode,
    message
  });
}

/**
 * Show the error overlay for unknown errors
 */
export function triggerUnknownError(message?: string) {
  errorOverlayState.set({
    visible: true,
    errorType: 'unknown',
    message
  });
}

/**
 * Hide the overlay (not really used since user will reload page)
 */
export function hideErrorOverlay() {
  errorOverlayState.set({
    visible: false,
    errorType: 'unknown'
  });
}