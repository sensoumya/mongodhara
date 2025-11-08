<script lang="ts">
  import { fade, scale } from "svelte/transition";

  export let show: boolean = false;
  export let maxWidth: string = "max-w-6xl";

  function handleBackdropClick() {
    show = false;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      show = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
  <div class="modal modal-open">
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <div
      class="modal-box {maxWidth} w-full max-h-[calc(100vh-16rem)] flex flex-col"
      on:click|stopPropagation
      role="dialog"
      tabindex="-1"
      in:scale={{ duration: 200, start: 0.95 }}
      out:scale={{ duration: 200, start: 0.95 }}
    >
      <div class="flex-1 overflow-y-auto">
        <slot />
      </div>
    </div>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      class="modal-backdrop"
      on:click={handleBackdropClick}
      in:fade={{ duration: 200 }}
      out:fade={{ duration: 200 }}
    ></div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
  }
</style>
