<script lang="ts">
  type BreadcrumbSegment = {
    name: string;
    href?: string;
    label?: string;
    isHome?: boolean;
    loading?: boolean;
  };

  export let segments: BreadcrumbSegment[];

  let copiedIndex: number | null = null;

  /**
   * Truncates a string by keeping the beginning and end with ellipsis in the middle
   * @param str The string to truncate
   * @param maxLength The maximum length before truncation (default: 30)
   * @returns The truncated string with ellipsis in the middle
   */
  function truncateMiddle(str: string, maxLength: number = 30): string {
    if (str.length <= maxLength) {
      return str;
    }
    const charsToShow = maxLength - 3; // Account for the ellipsis
    const frontChars = Math.ceil(charsToShow / 2);
    const backChars = Math.floor(charsToShow / 2);
    return (
      str.substring(0, frontChars) +
      "..." +
      str.substring(str.length - backChars)
    );
  }

  /**
   * Copies the segment name to clipboard
   */
  async function copyToClipboard(name: string, index: number) {
    try {
      await navigator.clipboard.writeText(name);
      copiedIndex = index;
      setTimeout(() => {
        copiedIndex = null;
      }, 200); // Reset after 200ms
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }
</script>

<div class="flex items-center text-sm">
  {#each segments as segment, i}
    {#if i > 0}
      <span class="mx-2 text-base-content/50">&gt;</span>
    {/if}

    {#if i < segments.length - 1}
      <a
        href={segment.href}
        class="rounded-lg {i === 0
          ? 'pl-2 pr-2 py-1'
          : 'px-2 py-1'} whitespace-nowrap"
      >
        {#if segment.isHome}
          <span
            class="badge badge-ghost border-transparent hover:bg-secondary/10 align-middle font-bold transition-all duration-300 hover:text-secondary"
          >
            {truncateMiddle(segment.name)}
          </span>
        {:else if segment.label}
          <span
            class="badge badge-ghost border-transparent hover:bg-secondary/10 align-middle transition-all duration-300 hover:text-secondary group"
          >
            <span class="font-bold">{segment.label}:</span>
            {#if segment.loading}
              <span class="loading loading-dots loading-sm mx-5"></span>
            {:else}
              <span>{truncateMiddle(segment.name)}</span>
              <button
                on:click|preventDefault|stopPropagation={() =>
                  copyToClipboard(segment.name, i)}
                class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:text-primary cursor-pointer"
                title="Copy"
                aria-label="Copy {segment.name}"
              >
                <i
                  class="fa {copiedIndex === i
                    ? 'fa-solid'
                    : 'fa-regular'} fa-copy text-xs"
                ></i>
              </button>
            {/if}
          </span>
        {:else}
          <span
            class="badge badge-ghost border-transparent hover:bg-secondary/10 align-middle font-bold transition-all duration-300 hover:text-secondary"
          >
            {truncateMiddle(segment.name)}
          </span>
        {/if}
      </a>
    {:else}
      <div
        class="{i === 0
          ? 'pl-2 pr-2 py-1'
          : 'px-2 py-1'} rounded-md whitespace-nowrap"
      >
        {#if segment.isHome}
          <span
            class="badge badge-ghost align-middle bg-transparent font-bold text-base-content/80"
          >
            {truncateMiddle(segment.name)}
          </span>
        {:else if segment.label}
          <span
            class="badge badge-ghost border-transparent align-middle bg-transparent text-base-content/80 group"
          >
            <span class="font-bold">{segment.label}:</span>
            {#if segment.loading}
              <span class="loading loading-dots loading-sm mx-5"></span>
            {:else}
              <span>{truncateMiddle(segment.name)}</span>
              <button
                on:click|stopPropagation={() =>
                  copyToClipboard(segment.name, i)}
                class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:text-primary cursor-pointer"
                title="Copy"
                aria-label="Copy {segment.name}"
              >
                <i
                  class="fa {copiedIndex === i
                    ? 'fa-solid'
                    : 'fa-regular'} fa-copy text-xs"
                ></i>
              </button>
            {/if}
          </span>
        {:else}
          <span
            class="badge badge-ghost border-transparent align-middle bg-transparent font-bold text-base-content/80"
          >
            {truncateMiddle(segment.name)}
          </span>
        {/if}
      </div>
    {/if}
  {/each}
</div>

<style>
  /* Tailwind styles are applied via classes */
</style>
