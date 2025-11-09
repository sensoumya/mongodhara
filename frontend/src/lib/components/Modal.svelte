<script lang="ts">
  import { fade, scale } from "svelte/transition";

  export let title: string;
  export let message: string;
  export let show: boolean = true;
  export let onConfirm: () => Promise<void> | void = () => {};
  export let onCancel: () => void = () => {};
  export let confirmButtonText: string = "Confirm";
  export let cancelButtonText: string = "Cancel";
  export let confirmDisabled: boolean = false;
  export let validationMessage: string = "";
  let isLoading = false;

  async function handleConfirm() {
    if (confirmDisabled) return;
    isLoading = true;
    try {
      if (onConfirm) {
        await onConfirm();
      }
    } finally {
      isLoading = false;
    }
  }

  /**
   * Splits the message into quoted and unquoted parts.
   * Supports both 'single' and "double" quotes.
   */
  function parseMessage(message: string) {
    const parts: { text: string; quoted: boolean }[] = [];
    const regex = /(['"])(.*?)\1/g; // Match '...' or "..."
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(message))) {
      if (match.index > lastIndex) {
        parts.push({
          text: message.slice(lastIndex, match.index),
          quoted: false,
        });
      }
      parts.push({
        text: match[0], // keep quotes
        quoted: true,
      });
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < message.length) {
      parts.push({
        text: message.slice(lastIndex),
        quoted: false,
      });
    }

    return parts;
  }
</script>

{#if show}
  <div
    class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-base-300/50"
    transition:fade={{ duration: 300 }}
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
    on:click|self={onCancel}
  >
    <div
      class="card bg-base-100 text-base-content w-full max-w-sm p-6 shadow-xl border border-base-200 rounded-lg"
      transition:scale={{ duration: 200, start: 0.95 }}
    >
      <div class="flex justify-between items-center mb-4">
        <h3 id="modal-title" class="text-xl poppins text-base-content">
          {title}
        </h3>
        <!-- <button
          on:click={onCancel}
          class="btn btn-circle btn-sm btn-ghost hover:text-error hover:bg-transparent hover:border-transparent"
          aria-label="Close modal"
          title="Close"
        >
          <i class="fa-solid fa-xmark"></i>
        </button> -->
      </div>

      {#if message}
        <p class="mb-6 text-base-content/80 whitespace-pre-wrap">
          {#each parseMessage(message) as part}
            <span class={part.quoted ? "break-all" : "break-normal"}>
              {part.text}
            </span>
          {/each}
        </p>
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
              {cancelButtonText}
            </button>
          {/if}

          {#if onConfirm}
            {#if confirmDisabled && validationMessage}
              <div class="tooltip tooltip-top" data-tip={validationMessage}>
                <button
                  on:click={handleConfirm}
                  class="btn btn-primary opacity-50 cursor-not-allowed"
                  disabled={true}
                >
                  {confirmButtonText}
                </button>
              </div>
            {:else}
              <button
                on:click={handleConfirm}
                class="btn btn-primary min-w-32 {isLoading
                  ? '!bg-primary !border-primary'
                  : ''}"
                disabled={isLoading}
              >
                {#if isLoading}
                  <span
                    class="loading loading-ring loading-sm !text-primary-content"
                  ></span>
                {:else}
                  {confirmButtonText}
                {/if}
              </button>
            {/if}
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}
