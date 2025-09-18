<script lang="ts">
  import { resolve } from "$app/paths";
  import type { BreadcrumbSegment } from "$lib/stores/types";
  export let segments: BreadcrumbSegment[];
  export let showBackButton: boolean = false;
</script>

<div class="flex items-center text-sm mb-6">
  {#if showBackButton}
    <button
      on:click={() => window.history.back()}
      class="text-base-content/70 hover:text-base-content transition-colors duration-300 mr-4"
      aria-label="Go back"
    >
      <i class="fas fa-arrow-left text-2xl"></i>
    </button>
  {/if}

  {#each segments as segment, i}
    <div class="flex items-center">
      {#if i > 0}
        <span class="mx-2 text-base-content/50">&gt;</span>
      {/if}

      {#if i < segments.length - 1}
        <a
          href={resolve(segment.href)}
          class="text-primary border-2 border-transparent rounded-lg hover:border-primary transition-colors duration-300 px-2 py-1"
        >
          {#if segment.isHome}
            <i class="fas fa-home mr-2"></i>
          {:else if i === 1}
            <span class="font-bold">Database:</span>
          {:else if i === 2}
            <span class="font-bold">Collection:</span>
          {/if}
          {segment.name}
        </a>
      {:else}
        <div class="px-3 py-1 bg-base-200 text-base-content rounded-md">
          {#if segment.isHome}
            <i class="fas fa-home mr-2"></i>
          {/if}
          {#if segment.label}
            <span class="font-bold">{segment.label}:</span>
          {/if}
          {segment.name}
        </div>
      {/if}
    </div>
  {/each}
</div>
