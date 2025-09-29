<script lang="ts">
  import type { BreadcrumbSegment } from "$lib/stores/types";
  export let segments: BreadcrumbSegment[];
</script>

<div class="flex items-center text-sm mb-6">
  {#each segments as segment, i}
    <div class="flex items-center">
      {#if i > 0}
        <span class="mx-2 text-base-content/50">&gt;</span>
      {/if}

      {#if i < segments.length - 1}
        <a
          href={segment.href}
          class="text-primary border-2 border-transparent rounded-lg hover:border-primary transition-colors duration-300 px-2 py-1 whitespace-nowrap"
        >
          {#if segment.isHome}
            <i class="fas fa-home mr-2 align-middle"></i>
          {:else if segment.label}
            <span class="font-bold align-middle">{segment.label}:</span>
          {/if}
          <span
            class="max-w-[200px] inline-block truncate overflow-hidden align-middle"
          >
            {segment.name}
          </span>
        </a>
      {:else}
        <div
          class="px-3 py-1 bg-base-200 text-base-content rounded-md whitespace-nowrap"
        >
          {#if segment.isHome}
            <i class="fas fa-home mr-2 align-middle"></i>
          {/if}
          {#if segment.label}
            <span class="font-bold align-middle">{segment.label}:</span>
          {/if}
          <span
            class="max-w-[200px] inline-block truncate overflow-hidden align-middle"
          >
            {segment.name}
          </span>
        </div>
      {/if}
    </div>
  {/each}
</div>
