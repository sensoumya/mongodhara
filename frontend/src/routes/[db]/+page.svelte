<script lang="ts">
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import { page } from "$app/stores";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import CollectionsView from "./components/CollectionsView.svelte";
  import DatabaseCarousel from "./components/DatabaseCarousel.svelte";
  import GridFSView from "./components/GridFSView.svelte";

  let { db } = $page.params;

  // Ensure db is not undefined
  $: dbName = db || "";

  // Shared state for pagination and search
  let currentPage: number = 1;
  let searchTerm: string = "";
  let loading: boolean = false;
  let carouselIndex: number = 0;
  let totalPages: number = 1;

  // Initialize carousel index based on URL parameter
  $: {
    const type = $page.url.searchParams.get("type");
    if (type === "gridfs") {
      carouselIndex = 1;
    } else {
      // Default to collections view (type=collection or no parameter)
      carouselIndex = 0;
    }
  }

  // Component references
  let collectionsView: CollectionsView;
  let gridfsView: GridFSView;

  // Response data from components
  let collectionsResponse: any = { collections: [], total: 0 };
  let gridfsResponse: any = { buckets: [], total: 0 };

  // Computed properties
  $: placeholder =
    carouselIndex === 0 ? "Search collection..." : "Search GridFS bucket...";

  /**
   * Handles carousel navigation and data fetching.
   */
  function handleCarouselChange(event: CustomEvent<{ index: number }>) {
    const newIndex = event.detail.index;
    carouselIndex = newIndex;
    currentPage = 1;
    searchTerm = "";

    // Update URL with appropriate type parameter
    const newType = newIndex === 0 ? "collection" : "gridfs";
    goto(`?type=${newType}`, { replaceState: true });

    // Use setTimeout to ensure component is mounted before fetching data
    setTimeout(() => {
      fetchData();
    }, 0);
  }

  /**
   * Handles search operations.
   */
  function handleSearch(event?: CustomEvent<{ term: string }>) {
    // If event is provided, use the term from the event detail
    // Otherwise, use the current searchTerm value (for form submission)
    if (event) {
      searchTerm = event.detail.term;
    }
    currentPage = 1;
    fetchData();
  }

  /**
   * Handles form submission for search.
   */
  function handleSearchSubmit() {
    currentPage = 1;
    fetchData();
  }

  /**
   * Handles page changes.
   */
  function handlePageChange(event: CustomEvent<{ page: number }>) {
    currentPage = event.detail.page;
    fetchData();
  }

  /**
   * Direct page change handler.
   */
  function changePage(page: number) {
    currentPage = page;
    fetchData();
  }

  /**
   * Handles create button clicks.
   */
  function handleCreate() {
    if (carouselIndex === 0) {
      collectionsView?.showCreateCollectionModal();
    } else {
      gridfsView?.openCreateBucketModal();
    }
  }

  /**
   * Fetches data based on current view.
   */
  function fetchData() {
    if (carouselIndex === 0) {
      collectionsView?.fetchCollections();
    } else {
      gridfsView?.fetchGridFSBuckets();
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    fetchData();
  });
</script>

<svelte:head>
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css"
    integrity="sha512-Kc323vGBEqzTmouAECnVceyQqyqdsSiqLQISBL29aUW4U/M7pSPA/gEUZQqv1cwx4OnYxTxve5UMg5GT6L4JJg=="
    crossorigin="anonymous"
    referrerpolicy="no-referrer"
  />
</svelte:head>

<div
  class="h-[calc(100vh-90px)] flex flex-col p-2 md:p-4 bg-base-100 text-base-content"
  transition:fade={{ duration: 200 }}
>
  <div class="max-w-7xl mx-auto w-full h-full flex flex-col">
    <div class="mb-4">
      <!-- Database Carousel Navigation -->
      <DatabaseCarousel
        currentIndex={carouselIndex}
        on:change={handleCarouselChange}
      />

      <!-- Breadcrumb -->
      <Breadcrumb
        showBackButton={true}
        segments={[
          { name: "Home", isHome: true, href: `${base}/` },
          { name: db || "", href: "", label: "Database" },
        ]}
      />

      <!-- Search and Create Controls -->
      <div
        class="flex flex-col md:flex-row justify-between items-center mb-4 space-y-2 md:space-y-0"
      >
        <form
          on:submit|preventDefault={handleSearchSubmit}
          class="relative w-full md:w-1/3 flex"
        >
          <label
            class="input input-bordered input-secondary flex items-center gap-2 w-full"
          >
            <input
              type="text"
              class="grow"
              bind:value={searchTerm}
              {placeholder}
            />
            {#if searchTerm}
              <button
                type="button"
                on:click={() => {
                  searchTerm = "";
                  handleSearchSubmit();
                }}
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
            <button
              type="submit"
              class="btn btn-sm btn-ghost"
              aria-label="Search"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                class="h-4 w-4 opacity-70"
              >
                <path
                  fill-rule="evenodd"
                  d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.094 2.093a.75.75 0 0 1-1.06 1.06l-2.094-2.094ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </label>
        </form>
        <button
          on:click={handleCreate}
          class="btn btn-secondary px-4 py-3 rounded-md transition-colors duration-300 tooltip"
          aria-label={carouselIndex === 0
            ? "Create new collection"
            : "Create new GridFS bucket"}
          data-tip={carouselIndex === 0
            ? "Create new collection"
            : "Create new GridFS bucket"}
        >
          <i class="fas fa-plus mr-0"></i>
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-grow overflow-y-auto mb-4 relative">
      {#if carouselIndex === 0}
        <CollectionsView
          bind:this={collectionsView}
          bind:collectionsResponse
          bind:totalPages
          db={dbName}
          {searchTerm}
          {currentPage}
          {loading}
        />
      {:else}
        <GridFSView
          bind:this={gridfsView}
          bind:gridfsResponse
          bind:totalPages
          db={dbName}
          {searchTerm}
          {currentPage}
          {loading}
        />
      {/if}
    </div>

    <!-- Pagination Controls -->
    <div
      class="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0"
    >
      <div class="text-sm text-secondary">
        {#if carouselIndex === 0}
          Displaying {collectionsResponse.collections?.length ===
          collectionsResponse.total
            ? "all"
            : `${(currentPage - 1) * 16 + 1} - ${Math.min(currentPage * 16, collectionsResponse.total || 0)}`}
          of {collectionsResponse.total || 0} collections
        {:else if carouselIndex === 1}
          Displaying {gridfsResponse.buckets?.length === gridfsResponse.total
            ? "all"
            : `${(currentPage - 1) * 16 + 1} - ${Math.min(currentPage * 16, gridfsResponse.total || 0)}`}
          of {gridfsResponse.total || 0} GridFS buckets
        {/if}
      </div>
      <div class="join">
        <button
          on:click={() => changePage(1)}
          disabled={currentPage === 1 || loading}
          class="join-item btn hover:text-accent/80"
          aria-label="First page"
        >
          «
        </button>
        <button
          on:click={() => changePage(currentPage - 1)}
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
            bind:value={currentPage}
            on:change={() => fetchData()}
            min="1"
            max={totalPages}
            class="input input-sm w-16 text-center input-neutral"
          />
          <span class="text-base-content">of {totalPages}</span>
        </div>
        <button
          on:click={() => changePage(currentPage + 1)}
          disabled={currentPage >= totalPages || loading}
          class="join-item btn hover:text-accent/80"
          aria-label="Next page"
        >
          ›
        </button>
        <button
          on:click={() => changePage(totalPages)}
          disabled={currentPage >= totalPages || loading}
          class="join-item btn hover:text-accent/80"
          aria-label="Last page"
        >
          »
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  /* Custom tooltip styles for long names */
  .tooltip:before {
    max-width: 300px;
    white-space: pre-wrap;
    word-break: break-word;
    text-align: left;
    line-height: 1.4;
  }

  /* Ensure tooltip content wraps properly */
  .tooltip[data-tip]:before {
    content: attr(data-tip);
  }
</style>
