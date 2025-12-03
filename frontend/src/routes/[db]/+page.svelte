<script lang="ts">
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import { page } from "$app/stores";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import Pagination from "$lib/components/Pagination.svelte";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import CollectionsView from "./components/CollectionsView.svelte";
  import DatabaseCarousel from "./components/DatabaseCarousel.svelte";
  import GridFSView from "./components/GridFSView.svelte";

  let { db } = $page.params;

  // Ensure db is not undefined
  $: dbId = db || "";

  // Database name derived from API responses
  $: dbName =
    collectionsResponse?.database?.name || gridfsResponse?.database?.name || "";

  /**
   * Checks if a database is a system database that should not be modified
   */
  function isSystemDatabase(dbName: string): boolean {
    const systemDatabases = ["admin", "local", "config", "mongodhara"];
    return systemDatabases.includes(dbName);
  }

  // Shared state for pagination and search
  let currentPage: number = 1;
  let searchTerm: string = "";
  let loading: boolean = false;
  let carouselIndex: number = 0;
  let totalPages: number = 1;
  let pageSize: number =
    typeof window !== "undefined"
      ? parseInt(localStorage.getItem("pageSize_collections") || "20")
      : 20;

  // Separate state for each tab to preserve pagination when switching
  let collectionsPage: number = 1;
  let collectionsSearchTerm: string = "";
  let gridfsPage: number = 1;
  let gridfsSearchTerm: string = "";

  // Track if each tab has loaded data to avoid unnecessary API calls on tab switch
  let collectionsLoaded: boolean = false;
  let gridfsLoaded: boolean = false;

  // Save pageSize to localStorage whenever it changes
  $: if (typeof window !== "undefined") {
    localStorage.setItem("pageSize_collections", pageSize.toString());
  }

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

  // Loading states from components
  let collectionsLoading: boolean = false;
  let gridfsLoading: boolean = false;

  // Computed properties
  $: placeholder =
    carouselIndex === 0 ? "Search collection..." : "Search GridFS bucket...";
  $: currentViewLoading =
    carouselIndex === 0 ? collectionsLoading : gridfsLoading;

  /**
   * Handles carousel navigation and data fetching.
   */
  function handleCarouselChange(event: CustomEvent<{ index: number }>) {
    const newIndex = event.detail.index;

    // Save current tab's state before switching
    if (carouselIndex === 0) {
      collectionsPage = currentPage;
      collectionsSearchTerm = searchTerm;
    } else {
      gridfsPage = currentPage;
      gridfsSearchTerm = searchTerm;
    }

    carouselIndex = newIndex;

    // Restore the new tab's state
    if (newIndex === 0) {
      currentPage = collectionsPage;
      searchTerm = collectionsSearchTerm;
    } else {
      currentPage = gridfsPage;
      searchTerm = gridfsSearchTerm;
    }

    // Update URL with appropriate type parameter
    const newType = newIndex === 0 ? "collection" : "gridfs";
    goto(`?type=${newType}`, { replaceState: true });

    // Only fetch data if the tab hasn't been loaded yet
    const tabHasData = newIndex === 0 ? collectionsLoaded : gridfsLoaded;
    if (!tabHasData) {
      setTimeout(() => {
        fetchData(false);
      }, 0);
    }
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

    // Update the current tab's state
    if (carouselIndex === 0) {
      collectionsPage = 1;
      collectionsSearchTerm = searchTerm;
      // Reset loaded state when search changes
      collectionsLoaded = false;
    } else {
      gridfsPage = 1;
      gridfsSearchTerm = searchTerm;
      // Reset loaded state when search changes
      gridfsLoaded = false;
    }

    fetchData();
  }

  /**
   * Handles form submission for search.
   */
  function handleSearchSubmit() {
    currentPage = 1;

    // Update the current tab's state
    if (carouselIndex === 0) {
      collectionsPage = 1;
      collectionsSearchTerm = searchTerm;
      // Reset loaded state when search changes
      collectionsLoaded = false;
    } else {
      gridfsPage = 1;
      gridfsSearchTerm = searchTerm;
      // Reset loaded state when search changes
      gridfsLoaded = false;
    }

    fetchData(true); // Always force refresh for search
  }

  function handlePageChange(event: CustomEvent<{ page: number }>) {
    currentPage = event.detail.page;

    // Update the current tab's state
    if (carouselIndex === 0) {
      collectionsPage = currentPage;
    } else {
      gridfsPage = currentPage;
    }

    fetchData(false); // Don't force refresh for pagination
  }

  /**
   * Direct page change handler.
   */
  function changePage(page: number) {
    currentPage = page;

    // Update the current tab's state
    if (carouselIndex === 0) {
      collectionsPage = currentPage;
    } else {
      gridfsPage = currentPage;
    }

    fetchData(false); // Don't force refresh for pagination
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
  function fetchData(forceRefresh: boolean = false) {
    if (carouselIndex === 0) {
      collectionsView?.fetchCollections(forceRefresh);
    } else {
      gridfsView?.fetchGridFSBuckets(forceRefresh);
    }
  }

  /**
   * Called by child components when data is successfully loaded
   */
  function handleDataLoaded() {
    if (carouselIndex === 0) {
      collectionsLoaded = true;
    } else {
      gridfsLoaded = true;
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
  class="h-[calc(100vh-90px)] flex flex-col px-2 pb-2 bg-base-100 text-base-content"
>
  <div class="max-w-7xl mx-auto w-full h-full flex flex-col">
    <div class="mb-2">
      <!-- Database Carousel Navigation -->
      <DatabaseCarousel
        currentIndex={carouselIndex}
        on:change={handleCarouselChange}
      />

      <!-- Breadcrumb and Controls Row -->
      <div
        class="flex flex-col md:flex-row md:items-center justify-between mb-2 gap-2"
      >
        <div class="flex-1">
          <Breadcrumb
            segments={[
              { name: "Home", isHome: true, href: `${base}/` },
              {
                name: dbName,
                href: "",
                label: "Database",
                loading: currentViewLoading && !dbName,
              },
            ]}
          />
        </div>
        <div class="flex items-center gap-2">
          <form
            on:submit|preventDefault={handleSearchSubmit}
            class="flex w-full max-w-xs"
          >
            <label
              class="input input-ghost input-sm flex items-center gap-2 w-full focus-within:outline-none"
            >
              <input
                type="text"
                class="text-base outline-none"
                bind:value={searchTerm}
                {placeholder}
              />
              <div class="flex items-center" style="width: 24px;">
                {#if searchTerm}
                  <button
                    type="button"
                    on:click={() => {
                      searchTerm = "";
                      handleSearchSubmit();
                    }}
                    class="btn btn-sm btn-ghost btn-circle"
                    aria-label="Clear search input"
                    in:fade={{ duration: 150 }}
                    out:fade={{ duration: 150 }}
                  >
                    <i class="fas fa-times"></i>
                  </button>
                {/if}
              </div>
              <button
                type="submit"
                class="btn btn-sm btn-ghost btn-circle"
                aria-label={searchTerm ? "Search" : "Reload"}
                disabled={currentViewLoading}
              >
                <i class="fas {searchTerm ? 'fa-search' : 'fa-rotate-right'}"
                ></i>
              </button>
            </label>
          </form>
          {#if !isSystemDatabase(dbName)}
            <button
              on:click={handleCreate}
              class="btn btn-secondary btn-sm flex items-center gap-1"
              aria-label={carouselIndex === 0
                ? "Create new collection"
                : "Create new GridFS bucket"}
            >
              <i class="fas fa-plus"></i>
              <span class="hidden md:inline">Create</span>
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Separator line -->
    <div class="border-t border-base-content/10 mb-2"></div>

    <!-- Main Content Area -->
    <div class="flex-grow overflow-y-auto mb-4 relative">
      {#if carouselIndex === 0}
        <CollectionsView
          bind:this={collectionsView}
          bind:collectionsResponse
          bind:totalPages
          bind:isLoading={collectionsLoading}
          db={dbId}
          {dbName}
          {searchTerm}
          {currentPage}
          {loading}
          {pageSize}
          onDataLoaded={handleDataLoaded}
        />
      {:else}
        <GridFSView
          bind:this={gridfsView}
          bind:gridfsResponse
          bind:totalPages
          bind:isLoading={gridfsLoading}
          db={dbId}
          {searchTerm}
          {currentPage}
          {loading}
          {pageSize}
          onDataLoaded={handleDataLoaded}
        />
      {/if}
    </div>

    <!-- Pagination Controls -->
    <Pagination
      {currentPage}
      {totalPages}
      loading={false}
      {pageSize}
      showPageSize={true}
      on:pageChange={handlePageChange}
      on:pageSizeChange={(e) => {
        pageSize = e.detail.pageSize;
        currentPage = 1;

        // Update the current tab's state and reset loaded state
        if (carouselIndex === 0) {
          collectionsPage = 1;
          collectionsLoaded = false;
        } else {
          gridfsPage = 1;
          gridfsLoaded = false;
        }

        fetchData(true); // Force refresh when page size changes
      }}
    />
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
