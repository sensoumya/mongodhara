<script lang="ts">
  import { notifications, removeNotification } from "$lib/stores/notifications";
  import { fade } from "svelte/transition";

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
</script>

<div
  class="fixed top-[64px] right-4 z-[9999] flex flex-col items-end space-y-2"
>
  {#each $notifications as notification (notification.id)}
    {@const config = typeToConfig[notification.type]}
    {#if config}
      <div
        on:click={() => removeNotification(notification.id)}
        class="alert {config.class} text-white cursor-pointer w-96 max-w-sm shadow-lg"
        in:fade={{ duration: 200 }}
        out:fade={{ duration: 200 }}
        role="alert"
        aria-live="polite"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-6 w-6 shrink-0 stroke-current"
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
        <span>{notification.message}</span>
      </div>
    {/if}
  {/each}
</div>
