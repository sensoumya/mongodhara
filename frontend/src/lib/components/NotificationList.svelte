<script lang="ts">
  import { notifications, removeNotification } from "$lib/stores/notifications";
  import { fade } from "svelte/transition";

  // Notification styling config
  const typeToConfig = {
    success: {
      class:
        "alert alert-soft max-sm:alert-vertical alert-success text-xs font-bold",
      svgPath: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    },
    error: {
      class:
        "alert alert-soft max-sm:alert-vertical alert-error text-xs font-bold",
      svgPath:
        "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z",
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
<div
  class="fixed top-[64px] right-4 z-[9999] flex flex-col items-end space-y-2"
>
  {#each $notifications as notification (notification.id)}
    {@const config = typeToConfig[notification.type]}
    {#if config}
      <div
        on:click={() => removeNotification(notification.id)}
        class="alert {config.class} text-white cursor-pointer max-w-sm shadow-lg flex flex-wrap items-center"
        in:fade={{ duration: 200 }}
        out:fade={{ duration: 200 }}
        role="alert"
        aria-live="polite"
      >
        <!-- Icon -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-6 w-6 shrink-0 stroke-current mr-2"
          fill="none"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d={config.svgPath}
          />
        </svg>

        <!-- Message with smart wrapping -->
        <span class="flex-1 whitespace-normal leading-snug">
          {#each parseMessage(notification.message) as part}
            <span class={part.quoted ? "break-all" : "break-normal"}>
              {part.text}
            </span>
          {/each}
        </span>
      </div>
    {/if}
  {/each}
</div>
