<script lang="ts">
  import { createEventDispatcher } from "svelte";

  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let totalPages: number = 1;
  export let loading: boolean = false;
  export let placeholder: string = "Search...";

  // New optional props for controlling visibility
  export let showSearch: boolean = true;
  export let showCreateButton: boolean = true;

  let newSearchTerm: string = searchTerm;
  let pageInput: number = currentPage;

  const dispatch = createEventDispatcher<{
    search: { term: string };
    pageChange: { page: number };
    create: void;
  }>();

  // Keep pageInput in sync with currentPage
  $: pageInput = currentPage;

  /**
   * Handles the search button click, resetting the page to 1.
   */
  function handleSearch() {
    dispatch("search", { term: newSearchTerm });
  }

  /**
   * Clears the search input and triggers a new fetch.
   */
  function clearSearch() {
    newSearchTerm = "";
    handleSearch();
  }

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

  function handleCreateClick() {
    dispatch("create");
  }
</script>

<div
  class="flex flex-col md:flex-row justify-between items-center mb-2 space-y-2 md:space-y-0"
  class:justify-center={!showSearch && !showCreateButton}
  class:justify-end={!showSearch && showCreateButton}
  class:justify-start={showSearch && !showCreateButton}
>
  {#if showSearch}
    <form
      on:submit|preventDefault={handleSearch}
      class="relative w-full md:w-1/3 flex"
    >
      <label
        class="input input-bordered input-secondary flex items-center gap-2 w-full"
      >
        <input
          type="text"
          class="grow"
          bind:value={newSearchTerm}
          {placeholder}
        />
        {#if newSearchTerm}
          <button
            type="button"
            on:click|stopPropagation={clearSearch}
            class="btn btn-sm btn-ghost"
            aria-label="Clear search input"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        {/if}
        <button type="submit" class="btn btn-sm btn-ghost" aria-label="Search">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            class="h-4 w-4 opacity-70"
            ><path
              fill-rule="evenodd"
              d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.094 2.093a.75.75 0 0 1-1.06 1.06l-2.094-2.094ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
              clip-rule="evenodd"
            /></svg
          >
        </button>
      </label>
    </form>
  {/if}

  {#if showCreateButton}
    <button
      on:click={handleCreateClick}
      class="btn btn-secondary px-4 py-3 rounded-md transition-colors duration-300 tooltip"
      aria-label="Create new item"
      data-tip="Create new item"
    >
      <i class="fas fa-plus mr-0"></i>
    </button>
  {/if}
</div>

<div
  class="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0"
>
  <slot name="pagination-info" />

  <div class="join">
    <button
      on:click={handleFirstPage}
      disabled={currentPage === 1 || loading}
      class="join-item btn hover:text-accent/80"
      aria-label="First page"
    >
      «
    </button>
    <button
      on:click={handlePrevPage}
      disabled={currentPage === 1 || loading}
      class="join-item btn hover:text-accent/80"
      aria-label="Previous page"
    >
      ‹
    </button>
    <div class="join-item flex items-center space-x-1 px-4">
      <span class="text-base-content">Page</span>
      <input
        type="number"
        bind:value={pageInput}
        on:change={handlePageInput}
        min="1"
        max={totalPages}
        class="input input-sm w-16 text-center input-accent"
      />
      <span class="text-base-content">of {totalPages}</span>
    </div>
    <button
      on:click={handleNextPage}
      disabled={currentPage >= totalPages || loading}
      class="join-item btn hover:text-accent/80"
      aria-label="Next page"
    >
      ›
    </button>
    <button
      on:click={handleLastPage}
      disabled={currentPage >= totalPages || loading}
      class="join-item btn hover:text-accent/80"
      aria-label="Last page"
    >
      »
    </button>
  </div>
</div>
