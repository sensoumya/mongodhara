<script lang="ts">
  import type { DatabaseListItem } from "$lib/stores/types";
  import { createEventDispatcher } from "svelte";
  import { fade } from "svelte/transition";

  // Unified props for all pages
  export let db: DatabaseListItem | undefined = undefined;
  export let showPopover: boolean = false;
  export let rowIndex: number = 0;
  export let totalRows: number = 0;

  // For collection/GridFS pages (new generic approach)
  export let data: any = null;
  export let loading: boolean = false;
  export let onClose: () => void = () => {};

  // Shared stats data
  export let stats: any = null;

  const dispatch = createEventDispatcher();

  // Use data if provided, otherwise use stats (for backward compatibility)
  $: displayData = data ? data.stats || data : stats;

  // Calculate if popover should be shown above
  $: showAbove = rowIndex >= totalRows - 6 && rowIndex >= 6;

  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function formatKey(key: string): string {
    return key
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  function formatValue(key: string, value: any): string {
    if (typeof value === "number" && key.toLowerCase().includes("size")) {
      return formatBytes(value);
    }
    if (typeof value === "number") {
      return value.toLocaleString();
    }
    return String(value);
  }

  function handleToggle() {
    if (db) {
      dispatch("toggle", { dbName: db.name, opaqueId: db.opaque_id });
    }
  }

  function handleClose() {
    if (onClose) {
      onClose();
    } else {
      dispatch("close");
    }
  }
</script>

<!-- Unified popover implementation for all pages -->
{#if showPopover}
  <div
    class="absolute z-50 p-0.5 shadow bg-base-100 rounded-box min-w-64 max-w-96 border border-base-300 cursor-default"
    style="left: 0; transform: translateX(-100%); {showAbove
      ? 'bottom: 100%; margin-bottom: 0.5rem;'
      : 'top: 100%; margin-top: 0.5rem;'}; pointer-events: auto;"
    in:fade={{ duration: 200 }}
    out:fade={{ duration: 200 }}
    on:click|stopPropagation
  >
    <div class="flex justify-end">
      <button
        on:click|stopPropagation={handleClose}
        class="text-neutral/50 rounded-full hover:text-error cursor-pointer"
        aria-label="Close stats"
      >
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
    <div
      class="h-32 overflow-hidden relative cursor-default"
      on:click|stopPropagation
    >
      {#if loading}
        <div
          class="absolute inset-0 flex items-center justify-center"
          transition:fade={{ duration: 200 }}
        >
          <span class="loading loading-ring loading-sm text-primary"></span>
        </div>
      {:else if displayData && typeof displayData === "object"}
        <div
          class="overflow-y-auto h-full p-2 space-y-1"
          transition:fade={{ duration: 200 }}
        >
          {#each Object.entries(displayData) as [key, value]}
            <div class="flex justify-between items-center text-sm">
              <span class="font-medium text-base-content/70"
                >{formatKey(key)}:</span
              >
              <span class="font-mono text-info">{formatValue(key, value)}</span>
            </div>
          {/each}
        </div>
      {:else}
        <div
          class="absolute inset-0 flex items-center justify-center text-base-content/50"
          transition:fade={{ duration: 200 }}
        >
          <span>No stats available</span>
        </div>
      {/if}
    </div>
  </div>
{/if}
