<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import Modal from "$lib/components/Modal.svelte";
  import StatsPopover from "$lib/components/StatsPopover.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { Collection, PaginatedCollections } from "$lib/stores/types";
  import { onDestroy, onMount } from "svelte";
  import { fade } from "svelte/transition";

  export let db: string;
  export let dbName: string = "";
  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let loading: boolean = false;
  export let pageSize: number = 16;
  export let isLoading: boolean = false;
  export let onDataLoaded: (() => void) | undefined = undefined;
  let error: boolean = false;

  export let collectionsResponse: PaginatedCollections = {
    database: {
      name: "",
      opaque_id: "",
    },
    collections: [],
    total: 0,
    page: 1,
    page_size: 16,
  };

  // Track previous fetch parameters to detect when we need to refetch
  let previousPage: number = 0;
  let previousPageSize: number = 0;
  let previousSearchTerm: string = "";

  let exportingCol: string | null = null;
  let showDeleteModal = false;
  let colToDelete: string | null = null;
  let colToDeleteName: string | null = null;
  let showCreateModal = false;
  let newCollectionName: string = "";

  // Stats popover state
  let showStatsPopover: string | null = null;
  let statsData: any = null;
  let statsLoading: boolean = false;
  let statsCache: { [key: string]: any } = {};
  let loadingStats: { [key: string]: boolean } = {};

  // Copy functionality
  let justCopied: string | null = null;

  /**
   * Checks if a database is a system database that should not be modified
   */
  function isSystemDatabase(dbName: string): boolean {
    const systemDatabases = ["admin", "local", "config", "mongodhara"];
    return systemDatabases.includes(dbName);
  }

  export let totalPages = Math.ceil(collectionsResponse.total / pageSize);
  $: totalPages = Math.ceil(collectionsResponse.total / pageSize);

  // Track which collection names are overflowing
  let overflowingCols = new Set<string>();

  // Svelte action to check text overflow
  function checkTextOverflow(element: HTMLElement, colName: string) {
    function updateOverflow() {
      // Small delay to ensure CSS is applied
      setTimeout(() => {
        const isOverflowing = element.scrollWidth > element.clientWidth;

        if (isOverflowing) {
          overflowingCols.add(colName);
        } else {
          overflowingCols.delete(colName);
        }
        overflowingCols = new Set(overflowingCols); // Trigger reactivity
      }, 10);
    }

    // Check initially
    updateOverflow();

    // Check on window resize
    const resizeHandler = () => updateOverflow();
    window.addEventListener("resize", resizeHandler);

    return {
      destroy() {
        window.removeEventListener("resize", resizeHandler);
      },
    };
  }

  // Click outside handler to close stats popover
  function handleClickOutside(event: MouseEvent) {
    if (!showStatsPopover) return;

    const target = event.target as HTMLElement;
    // Check if the click is outside the stats popover
    const popover = document.querySelector(".absolute.z-50");
    if (popover && !popover.contains(target)) {
      showStatsPopover = null;
      statsData = null;
      statsLoading = false;
    }
  }

  onMount(() => {
    if (browser) {
      document.addEventListener("click", handleClickOutside);
    }
  });

  onDestroy(() => {
    if (browser) {
      document.removeEventListener("click", handleClickOutside);
    }
  });

  /**
   * Navigates to the collection detail page.
   * @param collection The collection object to navigate to.
   */
  function handleCollectionClick(collection: Collection) {
    goto(
      `${base}/${collectionsResponse.database.opaque_id}/${collection.opaque_id}?type=collection`
    );
  }

  /**
   * Fetches the list of collections for the current database.
   */
  export async function fetchCollections(forceRefresh: boolean = false) {
    // Determine if we need to fetch based on changed parameters
    const paramsChanged =
      previousPage !== currentPage ||
      previousPageSize !== pageSize ||
      previousSearchTerm !== searchTerm;

    // Skip if data is already loaded and not forcing refresh and params haven't changed
    if (
      !forceRefresh &&
      !paramsChanged &&
      collectionsResponse.collections.length > 0
    ) {
      return;
    }

    // Update previous parameters
    previousPage = currentPage;
    previousPageSize = pageSize;
    previousSearchTerm = searchTerm;

    isLoading = true;
    error = false;
    try {
      const query = new URLSearchParams();

      if (searchTerm.trim() !== "") {
        query.append("search", searchTerm);
      }

      query.append("page", currentPage.toString());
      query.append("page_size", pageSize.toString());

      const response = await api.apiGet<PaginatedCollections>(
        `/db/${db}/col?${query.toString()}`
      );
      collectionsResponse = response;
      // Notify parent that data has been loaded
      if (onDataLoaded) {
        onDataLoaded();
      }
    } catch (e) {
      error = true;
      collectionsResponse = {
        database: {
          name: "",
          opaque_id: "",
        },
        collections: [],
        total: 0,
        page: 1,
        page_size: pageSize,
      };
      addNotification(e instanceof Error ? e.message : String(e), "error");
    } finally {
      isLoading = false;
    }
  }

  /**
   * Sets up the deletion confirmation modal.
   */
  function handleDeleteClick(col: string) {
    showDeleteModal = true;
    colToDelete = col;
  }

  /**
   * Shows the create collection modal.
   */
  export function showCreateCollectionModal() {
    showCreateModal = true;
  }

  /**
   * Confirms and performs the collection deletion.
   */
  async function confirmDelete() {
    if (!colToDelete) return;

    try {
      await api.apiDelete(`/db/${db}/col/${colToDelete}`);

      // Close modal and show page loader immediately after API call completes
      const colNameForNotification = colToDeleteName;
      showDeleteModal = false;
      colToDelete = null;
      colToDeleteName = null;

      // Show page loader while fetching updated data
      isLoading = true;

      addNotification(
        `Collection "${colNameForNotification}" deleted successfully.`,
        "success"
      );
      collectionsResponse.collections = []; // Clear cache to force refetch
      await fetchCollections();
    } catch (e) {
      showDeleteModal = false;
      colToDelete = null;
      colToDeleteName = null;
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Cancels the collection deletion.
   */
  function cancelDelete() {
    showDeleteModal = false;
    colToDelete = null;
    colToDeleteName = null;
  }

  /**
   * Handles the creation of a new collection.
   */
  async function handleCreateCollection() {
    try {
      await api.apiPost(`/db/col`, {
        db: dbName,
        name: newCollectionName,
      });
      addNotification(
        `Collection "${newCollectionName}" created successfully.`,
        "success"
      );
      showCreateModal = false;
      newCollectionName = "";
      currentPage = 1;
      collectionsResponse.collections = []; // Clear cache to force refetch
      await fetchCollections();
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Fetches collection data and triggers a download.
   */
  async function handleExport(colOpaqueId: string, colName: string) {
    exportingCol = colName;
    try {
      const response = await api.apiGet<any>(
        `/db/${db}/col/${colOpaqueId}/export`
      );

      if (response && response.documents) {
        const jsonContent = JSON.stringify(response.documents, null, 2);
        const blob = new Blob([jsonContent], { type: "application/json" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = `${colName}_export.json`;
        document.body.appendChild(a);
        a.click();

        URL.revokeObjectURL(url);
        document.body.removeChild(a);
        addNotification(
          `Collection "${colName}" exported successfully.`,
          "success"
        );
      } else {
        addNotification(
          "Failed to export collection. No data received.",
          "error"
        );
      }
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    } finally {
      exportingCol = null;
    }
  }

  /**
   * Toggles the stats popover for a collection.
   */
  async function toggleStats(colOpaqueId: string) {
    if (showStatsPopover === colOpaqueId) {
      // Close popover
      showStatsPopover = null;
      statsData = null;
      statsLoading = false;
      return;
    }

    // Open popover and fetch stats if not already loaded
    showStatsPopover = colOpaqueId;

    if (!statsCache[colOpaqueId]) {
      statsLoading = true;
      loadingStats[colOpaqueId] = true;
      loadingStats = { ...loadingStats }; // Trigger reactivity
      statsData = null;

      try {
        const response = await api.apiGet<any>(
          `/db/${db}/col/${colOpaqueId}/stats`
        );
        statsCache[colOpaqueId] = response;
        statsData = response;
      } catch (e) {
        addNotification(
          `Failed to load stats: ${e instanceof Error ? e.message : String(e)}`,
          "error"
        );
        showStatsPopover = null;
      } finally {
        statsLoading = false;
        loadingStats[colOpaqueId] = false;
        loadingStats = { ...loadingStats }; // Trigger reactivity
      }
    } else {
      // Use cached data
      statsData = statsCache[colOpaqueId];
      statsLoading = false;
    }
  }

  /**
   * Copies collection name to clipboard
   */
  async function copyCollectionName(collectionName: string) {
    try {
      await navigator.clipboard.writeText(collectionName);
      justCopied = collectionName;
      setTimeout(() => {
        justCopied = null;
      }, 200); // Reset after 200ms
    } catch (e) {
      addNotification("Failed to copy to clipboard", "error");
    }
  }

  /**
   * Checks if a collection should be protected from deletion
   */
  function isProtectedCollection(
    collectionName: string,
    dbName: string
  ): boolean {
    const systemDatabases = ["admin", "local", "config", "mongodhara"];
    const systemCollections = [
      "system.users",
      "system.roles",
      "system.version",
      "system.namespaces",
    ];

    // Protect all collections in system databases
    if (systemDatabases.includes(dbName)) {
      return true;
    }

    // Protect specific system collections in any database
    return systemCollections.includes(collectionName);
  }
</script>

<div class="flex-grow overflow-y-auto pb-4 relative h-full">
  {#if isLoading}
    <div
      class="flex flex-col items-center justify-center h-full absolute inset-0 bg-base-100"
      in:fade={{ duration: 400 }}
      out:fade={{ duration: 400 }}
      aria-live="polite"
      aria-busy={isLoading}
    >
      <span
        class="loading loading-ring text-primary"
        style="width: 80px; height: 80px;"
      ></span>
    </div>
  {:else}
    <div
      class="transition-opacity duration-500 h-full"
      in:fade={{ duration: 400 }}
      out:fade={{ duration: 400 }}
    >
      {#if error}
        <div
          class="text-center text-secondary/40 h-full flex flex-col justify-center items-center"
        >
          <p class="text-2xl font-semibold poppins">Unable to load content</p>
        </div>
      {:else if collectionsResponse.collections.length === 0}
        <div
          class="text-center text-secondary/60 h-full flex flex-col justify-center items-center"
        >
          <p class="text-2xl font-semibold poppins">No collections available</p>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-1 p-1">
          {#each collectionsResponse.collections as collection, index (collection.opaque_id)}
            {@const isLastRow =
              index >= collectionsResponse.collections.length - 4}
            {@const hasTooltip = overflowingCols.has(collection.name)}
            <div
              class="card group shadow-sm cursor-pointer hover:bg-neutral/20 transition-all duration-200 ease-in-out h-14 {hasTooltip
                ? `tooltip ${isLastRow ? 'tooltip-top' : 'tooltip-bottom'}`
                : ''}"
              data-tip={hasTooltip ? collection.name : null}
              role="button"
              tabindex="0"
              on:click={() => handleCollectionClick(collection)}
              on:keydown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleCollectionClick(collection);
                }
              }}
              style="position: relative;"
            >
              <div
                class="card-body px-2 py-1 flex-row justify-between items-center"
              >
                <div class="flex-1 mr-3 overflow-hidden" style="min-width: 0;">
                  <span
                    use:checkTextOverflow={collection.name}
                    class="card-title text-base poppins font-normal transition-colors duration-200 block overflow-hidden text-ellipsis whitespace-nowrap"
                  >
                    {collection.name}
                  </span>
                </div>
                <div class="flex items-center gap-0.5 flex-shrink-0 relative">
                  <div class="relative">
                    <button
                      on:click|stopPropagation={() =>
                        toggleStats(collection.opaque_id)}
                      class="tooltip tooltip-left hover:text-info px-2 rounded-full cursor-pointer"
                      data-tip={`View Stats`}
                      aria-label={`View stats for ${collection.name}`}
                    >
                      <i class="fas fa-chart-bar"></i>
                    </button>
                    {#if showStatsPopover === collection.opaque_id}
                      <div
                        in:fade={{ duration: 200 }}
                        out:fade={{ duration: 200 }}
                      >
                        <StatsPopover
                          data={statsData}
                          loading={loadingStats[collection.opaque_id] || false}
                          showPopover={true}
                          rowIndex={index}
                          totalRows={collectionsResponse.collections.length}
                          onClose={() => {
                            showStatsPopover = null;
                            statsData = null;
                            statsLoading = false;
                          }}
                        />
                      </div>
                    {/if}
                  </div>
                  <button
                    on:click|stopPropagation={() =>
                      handleExport(collection.opaque_id, collection.name)}
                    class="tooltip tooltip-left hover:text-secondary px-2 rounded-full cursor-pointer"
                    data-tip={`Export as JSON`}
                    aria-label={`Export collection ${collection.name}`}
                    disabled={exportingCol === collection.name}
                  >
                    {#if exportingCol === collection.name}
                      <span class="loading loading-ring loading-sm"></span>
                    {:else}
                      <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    {/if}
                  </button>
                  <button
                    on:click|stopPropagation={() =>
                      copyCollectionName(collection.name)}
                    class="tooltip tooltip-left hover:text-primary px-2 rounded-full cursor-pointer"
                    data-tip="Copy"
                    aria-label={`Copy collection name ${collection.name}`}
                  >
                    <i
                      class="fa {justCopied === collection.name
                        ? 'fa-solid'
                        : 'fa-regular'} fa-copy"
                    ></i>
                  </button>
                  <button
                    on:click|stopPropagation={() => {
                      colToDelete = collection.opaque_id;
                      colToDeleteName = collection.name;
                      showDeleteModal = true;
                    }}
                    class="tooltip tooltip-left {isProtectedCollection(
                      collection.name,
                      dbName
                    )
                      ? 'text-base-content/30 cursor-not-allowed'
                      : 'hover:text-error cursor-pointer'} px-2 rounded-full"
                    data-tip={isProtectedCollection(collection.name, dbName)
                      ? "Cannot delete protected collection"
                      : "Delete"}
                    aria-label={`Delete collection ${collection.name}`}
                    disabled={isProtectedCollection(collection.name, dbName)}
                  >
                    <i class="fas fa-trash-alt"></i>
                  </button>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<Modal
  title="Confirm Deletion"
  message={`Are you sure you want to delete the collection "${colToDeleteName}"? This action cannot be undone.`}
  onConfirm={confirmDelete}
  onCancel={cancelDelete}
  show={showDeleteModal}
/>

<Modal
  title="Create New Collection"
  message=""
  onConfirm={handleCreateCollection}
  onCancel={() => {
    showCreateModal = false;
    newCollectionName = "";
  }}
  confirmButtonText="Create"
  cancelButtonText="Cancel"
  show={showCreateModal}
>
  <div class="form-control">
    <label class="label" for="newCollectionName">
      <span class="label-text">Collection Name</span>
    </label>
    <input
      type="text"
      id="newCollectionName"
      bind:value={newCollectionName}
      placeholder="Enter collection name"
      class="input input-bordered w-full"
    />
  </div>
</Modal>

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }

  /* Custom tooltip styles for long collection names */
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
