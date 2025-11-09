<script lang="ts">
  import { notifications, removeNotification } from "$lib/stores/notifications";
  import { fade } from "svelte/transition";

  // Notification styling config
  const typeToConfig = {
    success: {
      class:
        "alert alert-soft max-sm:alert-vertical alert-success text-xs font-bold",
    },
    error: {
      class:
        "alert alert-soft max-sm:alert-vertical alert-error text-xs font-bold",
    },
  };

  /**
   * Splits a message into quoted and unquoted parts.
   * Supports both 'single' and "double" quotes.
   */
  function parseMessage(message: string) {
    const parts: { text: string; quoted: boolean }[] = [];
    const regex = /(['"])(.*?)\1/g; // Match quoted text with either ' or "
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
        text: match[0], // include the quote characters
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

<!-- Notification container -->
<div class="fixed top-16 right-4 z-[9999] flex flex-col items-end space-y-2">
  {#each $notifications as notification (notification.id)}
    {@const config = typeToConfig[notification.type]}
    {#if config}
      <button
        on:click={() => removeNotification(notification.id)}
        class="alert {config.class} cursor-pointer max-w-sm shadow-lg flex flex-wrap items-center w-full text-left"
        in:fade={{ duration: 200 }}
        out:fade={{ duration: 200 }}
        aria-live="polite"
      >
        <!-- Icon -->
        {#if notification.type === "success"}
          <i class="fa-regular fa-circle-check text-current text-lg"></i>
        {:else if notification.type === "error"}
          <i class="fa-regular fa-circle-xmark text-current text-lg"></i>
        {/if}

        <!-- Message with smart wrapping -->
        <span class="flex-1 whitespace-normal leading-snug">
          {#each parseMessage(notification.message) as part}
            <span class={part.quoted ? "break-all" : "break-normal"}>
              {part.text}
            </span>
          {/each}
        </span>
      </button>
    {/if}
  {/each}
</div>
