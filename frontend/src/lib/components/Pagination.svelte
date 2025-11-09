<script lang="ts">
  import { createEventDispatcher } from "svelte";

  export let currentPage: number = 1;
  export let totalPages: number = 1;
  export let loading: boolean = false;
  export let pageSize: number = 20;
  export let showPageSize: boolean = true;

  let pageInput: number = currentPage;

  const dispatch = createEventDispatcher<{
    pageChange: { page: number };
    pageSizeChange: { pageSize: number };
  }>();

  // Keep pageInput in sync with currentPage
  $: pageInput = currentPage;

  /**
   * Handles the change event for the page input field.
   */
  function handlePageInput(event: Event) {
    const value = parseInt((event.target as HTMLInputElement).value, 10);
    if (!isNaN(value) && value > 0 && value <= totalPages) {
      dispatch("pageChange", { page: value });
    }
  }

  /**
   * Navigation functions
   */
  function handleNextPage() {
    if (currentPage < totalPages) {
      dispatch("pageChange", { page: currentPage + 1 });
    }
  }

  function handlePrevPage() {
    if (currentPage > 1) {
      dispatch("pageChange", { page: currentPage - 1 });
    }
  }

  function handleFirstPage() {
    if (currentPage !== 1) {
      dispatch("pageChange", { page: 1 });
    }
  }

  function handleLastPage() {
    if (currentPage !== totalPages) {
      dispatch("pageChange", { page: totalPages });
    }
  }

  function handlePageSizeChange() {
    dispatch("pageSizeChange", { pageSize });
  }
</script>

<div
  class="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0"
>
  {#if showPageSize}
    <div
      class="text-sm text-base-content flex flex-row items-center gap-2 whitespace-nowrap"
    >
      <span>Displaying</span>
      <select
        class="select select-xs select-bordered select-accent"
        bind:value={pageSize}
        on:change={handlePageSizeChange}
      >
        <option value={10}>10</option>
        <option value={14}>14</option>
        <option value={20}>20</option>
        <option value={50}>50</option>
      </select>
      <span>items per page</span>
    </div>
  {:else}
    <slot name="pagination-info" />
  {/if}

  <div class="join">
    <button
      on:click={handleFirstPage}
      disabled={currentPage === 1 || loading}
      class="join-item btn btn-sm hover:text-accent/80"
      aria-label="First page"
    >
      «
    </button>
    <button
      on:click={handlePrevPage}
      disabled={currentPage === 1 || loading}
      class="join-item btn btn-sm hover:text-accent/80"
      aria-label="Previous page"
    >
      ‹
    </button>
    <div class="join-item flex items-center space-x-1 px-3 text-sm">
      <span class="text-base-content">Page</span>
      <input
        type="number"
        bind:value={pageInput}
        on:change={handlePageInput}
        min="1"
        max={totalPages}
        class="input input-xs w-14 text-center input-accent"
      />
      <span class="text-base-content">of {totalPages}</span>
    </div>
    <button
      on:click={handleNextPage}
      disabled={currentPage >= totalPages || loading}
      class="join-item btn btn-sm hover:text-accent/80"
      aria-label="Next page"
    >
      ›
    </button>
    <button
      on:click={handleLastPage}
      disabled={currentPage >= totalPages || loading}
      class="join-item btn btn-sm hover:text-accent/80"
      aria-label="Last page"
    >
      »
    </button>
  </div>
</div>
