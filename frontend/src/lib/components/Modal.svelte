<script lang="ts">
  import { fade } from "svelte/transition";
  export let title: string;
  export let message: string;
  export let onConfirm: () => Promise<void> | void = () => {};
  export let onCancel: () => void = () => {};
  let isLoading = false;

  async function handleConfirm() {
    isLoading = true;
    try {
      if (onConfirm) {
        // Ensure onConfirm is awaited if it's an async function
        await onConfirm();
      }
    } finally {
      isLoading = false;
    }
  }
</script>

<div
  class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-base-300/50"
  transition:fade={{ duration: 300 }}
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
>
  <div
    class="card bg-base-100 text-base-content w-full max-w-sm p-6 shadow-xl border border-base-200 rounded-lg"
  >
    <div class="flex justify-between items-center mb-4">
      <h3 id="modal-title" class="text-xl font-semibold text-base-content">
        {title}
      </h3>
      <button
        on:click={onCancel}
        class="btn btn-circle btn-ghost"
        aria-label="Close modal"
        title="Close"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-6 w-6 stroke-current"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
    {#if message}
      <p class="mb-6 text-base-content/80">{message}</p>
    {/if}
    <slot />
    {#if onConfirm || onCancel}
      <div class="modal-action">
        {#if onCancel}
          <button
            on:click={onCancel}
            class="btn btn-outline"
            disabled={isLoading}
          >
            Cancel
          </button>
        {/if}
        {#if onConfirm}
          <button
            on:click={handleConfirm}
            class="btn btn-primary"
            disabled={isLoading}
          >
            {#if isLoading}
              <span class="loading loading-spinner loading-sm"></span>
            {:else}
              Confirm
            {/if}
          </button>
        {/if}
      </div>
    {/if}
  </div>
</div>
