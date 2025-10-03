import { triggerNetworkError, triggerUnknownError } from '$lib/stores/error-overlay';
import type { HandleClientError } from '@sveltejs/kit';

export const handleError: HandleClientError = ({ error, event }) => {
  // Log the error for debugging
  console.error('Client error:', error, event);

  // Show the error overlay for UI component failures
  triggerUnknownError(
    error instanceof Error ? error.message : 'Failed to load page component'
  );

  // Return error details (SvelteKit requirement)
  return {
    message: error instanceof Error ? error.message : 'Component loading failed',
    code: 'COMPONENT_ERROR'
  };
};

// Global error handler for UI component failures and unhandled errors
if (typeof window !== 'undefined') {
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    
    triggerNetworkError('Failed to load component. Please refresh the page.');
  });

  window.addEventListener('error', (event) => {
    console.error('Component error:', event.error);
    
    triggerUnknownError(
      event.error?.message || 'Component failed to load properly'
    );
  });
}