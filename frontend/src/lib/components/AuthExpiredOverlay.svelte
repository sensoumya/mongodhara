<script lang="ts">
  import { errorOverlayState } from "$lib/stores/error-overlay";
  import { fade } from "svelte/transition";

  function handleReload() {
    window.location.reload();
  }

  // Get error-specific content
  $: errorContent = getErrorContent(
    $errorOverlayState.errorType,
    $errorOverlayState.statusCode
  );

  function getErrorContent(errorType: string, statusCode?: number) {
    switch (errorType) {
      case "auth":
        return {
          icon: "fas fa-lock",
          title: "Session Expired",
          message:
            "Your session has expired. Please reload the page to sign in again.",
        };
      case "network":
        return {
          icon: "fas fa-wifi",
          title: "Connection Error",
          message:
            "Unable to connect to the server. Please check your internet connection and try again.",
        };
      case "server":
        return {
          icon: "fas fa-server",
          title: "Server Error",
          message: `The server encountered an error${statusCode ? ` (${statusCode})` : ""}. Please reload the page to continue.`,
        };
      default:
        return {
          icon: "fas fa-exclamation-triangle",
          title: "Something Went Wrong",
          message:
            "An unexpected error occurred. Please reload the page to continue.",
        };
    }
  }
</script>

{#if $errorOverlayState.visible}
  <!-- Hazy backdrop -->
  <div
    class="fixed inset-0 z-40"
    style="backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); background: rgba(0, 0, 0, 0.3);"
    in:fade={{ duration: 300 }}
    out:fade={{ duration: 300 }}
  ></div>

  <!-- Error overlay content -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center"
    style="background: 
      radial-gradient(circle at 25% 25%, hsl(var(--b2) / 0.3) 0%, transparent 50%),
      radial-gradient(circle at 75% 75%, hsl(var(--b3) / 0.2) 0%, transparent 50%),
      repeating-conic-gradient(from 0deg at 50% 50%, 
        hsl(var(--b1)) 0deg, 
        hsl(var(--b2) / 0.8) 1deg, 
        hsl(var(--b1)) 2deg
      ),
      hsl(var(--b1) / 0.95)"
    in:fade={{ duration: 300, delay: 100 }}
    out:fade={{ duration: 300 }}
  >
    <div
      class="bg-base-100 rounded-lg shadow-2xl p-8 max-w-md mx-4 text-center border border-base-300"
    >
      <div class="text-error mb-4">
        <i class="{errorContent.icon} text-4xl"></i>
      </div>

      <h2 class="text-2xl font-bold text-base-content mb-2">
        {errorContent.title}
      </h2>

      <p class="text-base-content/70 mb-6">
        {errorContent.message}
      </p>

      {#if $errorOverlayState.message}
        <div
          class="bg-base-200 rounded p-3 mb-4 text-sm text-base-content/60 overflow-x-auto whitespace-pre-wrap break-words"
        >
          <strong>Details:</strong>
          <div class="mt-1 max-h-48 overflow-y-auto font-mono text-xs">
            {$errorOverlayState.message}
          </div>
        </div>
      {/if}

      <!-- <button on:click={handleReload} class="btn btn-primary btn-lg gap-2">
        <i class="fas fa-refresh"></i>
        Reload Page
      </button> -->
    </div>
  </div>
{/if}
