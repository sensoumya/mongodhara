<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import Pagination from "$lib/components/Pagination.svelte";
  import StatsPopover from "$lib/components/StatsPopover.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedDatabases } from "$lib/stores/types";
  import { onDestroy, onMount } from "svelte";
  import { fade } from "svelte/transition";

  let databasesResponse: PaginatedDatabases = {
    databases: [],
    total: 0,
    page: 1,
    page_size: 20,
  };
  let loading = true;
  let error = false;
  let showDeleteModal = false;
  let dbToDelete: string | null = null;
  let dbToDeleteName: string | null = null;
  let showCreateModal = false;
  let newDbName: string = "";
  let newCollectionName: string = "";

  // Stats state
  let showStatsPopover: string | null = null;
  let dbStats: { [key: string]: any } = {};
  let loadingStats: { [key: string]: boolean } = {};

  // Search and pagination state
  let searchTerm: string = "";
  let currentPage: number = 1;
  let pageSize: number =
    typeof window !== "undefined"
      ? parseInt(localStorage.getItem("pageSize_databases") || "20")
      : 20;
  $: totalPages = Math.ceil(databasesResponse.total / pageSize);

  // Save pageSize to localStorage whenever it changes
  $: if (typeof window !== "undefined") {
    localStorage.setItem("pageSize_databases", pageSize.toString());
  }

  // Track which database names are overflowing
  let overflowingDbs = new Set<string>();

  // Track which database copy button was just clicked
  let justCopied: string | null = null;

  // Svelte action to check text overflow
  function checkTextOverflow(element: HTMLElement, dbName: string) {
    function updateOverflow() {
      // Small delay to ensure CSS is applied
      setTimeout(() => {
        const isOverflowing = element.scrollWidth > element.clientWidth;

        if (isOverflowing) {
          overflowingDbs.add(dbName);
        } else {
          overflowingDbs.delete(dbName);
        }
        overflowingDbs = new Set(overflowingDbs); // Trigger reactivity
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

  // Click outside handler to close popover
  function handleClickOutside(event: MouseEvent) {
    if (!browser || !showStatsPopover) return;

    const target = event.target as HTMLElement;
    // Check if the click is outside any dropdown
    const dropdowns = document.querySelectorAll(".dropdown");
    let clickedInsideDropdown = false;

    dropdowns.forEach((dropdown) => {
      if (dropdown.contains(target)) {
        clickedInsideDropdown = true;
      }
    });

    if (!clickedInsideDropdown) {
      showStatsPopover = null;
    }
  }

  // Computed validation state
  $: createFormValid =
    newDbName.trim() !== "" &&
    newCollectionName.trim() !== "" &&
    !isSystemDatabase(newDbName.trim());
  $: validationMessage =
    !newDbName.trim() && !newCollectionName.trim()
      ? "Please fill in Database Name and Collection Name"
      : !newDbName.trim()
        ? "Please fill in Database Name"
        : !newCollectionName.trim()
          ? "Please fill in Collection Name"
          : isSystemDatabase(newDbName.trim())
            ? "Cannot create system database"
            : "";

  /**
   * Fetches the list of databases.
   */
  async function fetchDatabases() {
    loading = true;
    error = false;
    try {
      const query = new URLSearchParams();
      if (searchTerm.trim() !== "") {
        query.append("search", searchTerm);
      }
      query.append("page", currentPage.toString());
      query.append("page_size", pageSize.toString());

      const response = await api.apiGet<PaginatedDatabases>(
        `/db?${query.toString()}`
      );
      databasesResponse = response;
    } catch (e) {
      error = true;
      databasesResponse = {
        databases: [],
        total: 0,
        page: 1,
        page_size: pageSize,
      };
      addNotification((e as Error).message, "error");
    } finally {
      loading = false;
    }
  }

  /**
   * Handles search operations.
   */
  function handleSearch(event: CustomEvent<{ term: string }>) {
    searchTerm = event.detail.term;
    currentPage = 1;
    fetchDatabases();
  }

  /**
   * Handles page changes.
   */
  function handlePageChange(event: CustomEvent<{ page: number }>) {
    currentPage = event.detail.page;
    fetchDatabases();
  }

  /**
   * Handles create button clicks.
   */
  function handleCreate() {
    showCreateModal = true;
  }

  /**
   * Navigates to the collections view for a specific database.
   * @param db The opaque_id of the database to navigate to.
   */
  function handleDatabaseClick(db: string) {
    goto(`${base}/${db}?type=collection`);
  }

  /**
   * Sets up the deletion confirmation modal.
   * @param dbId The opaque_id of the database to delete.
   * @param dbName The display name of the database.
   */
  function handleDeleteClick(dbId: string, dbName: string) {
    showDeleteModal = true;
    dbToDelete = dbId;
    dbToDeleteName = dbName;
  }

  /**
   * Copies the database name to clipboard.
   * @param dbName The name to copy.
   */
  async function copyDatabaseName(dbName: string) {
    try {
      await navigator.clipboard.writeText(dbName);
      justCopied = dbName;
      setTimeout(() => {
        justCopied = null;
      }, 200); // Reset after 200ms
    } catch (e) {
      addNotification("Failed to copy to clipboard", "error");
    }
  }

  /**
   * Confirms and performs the database deletion.
   */
  async function confirmDelete() {
    if (!dbToDelete) return;

    try {
      await api.apiDelete(`/db/${dbToDelete}`);

      // Close modal and show page loader immediately after API call completes
      const dbNameForNotification = dbToDeleteName;
      showDeleteModal = false;
      dbToDelete = null;
      dbToDeleteName = null;

      // Show page loader while fetching updated data
      loading = true;

      addNotification(
        `Database "${dbNameForNotification}" deleted successfully.`,
        "success"
      );
      await fetchDatabases();
    } catch (e) {
      showDeleteModal = false;
      dbToDelete = null;
      dbToDeleteName = null;
      addNotification((e as Error).message, "error");
    }
  }

  /**
   * Cancels the database deletion.
   */
  function cancelDelete() {
    showDeleteModal = false;
    dbToDelete = null;
    dbToDeleteName = null;
  }

  /**
   * Handles the click on the "Create Database" button.
   */
  function handleCreateClick() {
    showCreateModal = true;
  }

  /**
   * Checks if a database is a system database that should not be deleted
   */
  function isSystemDatabase(dbName: string): boolean {
    const systemDatabases = ["admin", "local", "config", "mongodhara"];
    return systemDatabases.includes(dbName);
  }
  async function toggleStats(dbName: string, opaqueId?: string) {
    const dbKey = opaqueId ?? dbName;

    if (showStatsPopover === dbKey) {
      // Close popover
      showStatsPopover = null;
    } else {
      // Open popover and fetch stats if not already loaded
      showStatsPopover = dbKey;

      if (!dbStats[dbKey]) {
        loadingStats[dbKey] = true;
        loadingStats = { ...loadingStats }; // Trigger reactivity

        try {
          const statsResponse = await api.apiGet(`/db/${dbKey}/stats`);
          if (statsResponse) {
            // Handle both array and object responses
            const stats = Array.isArray(statsResponse)
              ? statsResponse[0]
              : statsResponse;
            dbStats[dbKey] = stats.stats || stats;
          }
        } catch (e) {
          addNotification(`Failed to load stats for ${dbKey}`, "error");
          showStatsPopover = null; // Close popover on error
        } finally {
          loadingStats[dbKey] = false;
          loadingStats = { ...loadingStats }; // Trigger reactivity
        }

        dbStats = { ...dbStats }; // Trigger reactivity
      }
    }
  }

  /**
   * Handles stats popover toggle events from the component.
   */
  function handleStatsToggle(
    event: CustomEvent<{ dbName: string; opaqueId?: string }>
  ) {
    const { dbName, opaqueId } = event.detail;
    toggleStats(dbName, opaqueId);
  }

  /**
   * Handles stats popover close events from the component.
   */
  function handleStatsClose() {
    showStatsPopover = null;
  }
  async function handleCreateDatabase() {
    if (!createFormValid) return;

    try {
      await api.apiPost(`/db/col`, {
        db: newDbName,
        name: newCollectionName,
      });
      addNotification(
        `Database "${newDbName}" with collection "${newCollectionName}" created successfully.`,
        "success"
      );
      showCreateModal = false;
      newDbName = ""; // Clear the input
      newCollectionName = ""; // Clear the input
      currentPage = 1; // Go back to the first page to see the new database
      await fetchDatabases();
    } catch (e) {
      addNotification((e as Error).message, "error");
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    fetchDatabases();
    if (browser) {
      document.addEventListener("click", handleClickOutside);
    }
  });

  onDestroy(() => {
    if (browser) {
      document.removeEventListener("click", handleClickOutside);
    }
  });
</script>

<div
  class="h-[calc(100vh-90px)] flex flex-col px-2 pb-2 bg-base-100 text-base-content"
>
  <div class="max-w-7xl mx-auto w-full h-full flex flex-col">
    <div class="mb-2">
      <h1
        class="text-2xl poppins mb-8 text-center flex items-center justify-center gap-4"
      >
        <span class="flex items-center gap-2">
          <i class="fas fa-database text-primary"></i>
          <span>Databases</span>
        </span>
      </h1>

      <!-- Breadcrumb and Controls Row -->
      <div
        class="flex flex-col md:flex-row md:items-center justify-between mb-2 gap-2"
      >
        <div class="flex-1">
          <Breadcrumb
            segments={[{ name: "Home", isHome: true, href: `${base}/db` }]}
          />
        </div>
        <div class="flex items-center gap-2">
          <form
            on:submit|preventDefault={() =>
              handleSearch({ detail: { term: searchTerm } })}
            class="flex w-full max-w-xs"
          >
            <label
              class="input input-ghost input-sm flex items-center gap-2 w-full focus-within:outline-none"
            >
              <input
                type="text"
                class="text-base outline-none"
                bind:value={searchTerm}
                placeholder="Search database..."
              />
              <div class="flex items-center" style="width: 24px;">
                {#if searchTerm}
                  <button
                    type="button"
                    on:click={() => {
                      searchTerm = "";
                      handleSearch({ detail: { term: "" } });
                    }}
                    class="btn btn-sm btn-ghost btn-circle"
                    disabled={loading}
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
                disabled={loading}
                aria-label={searchTerm ? "Search" : "Reload"}
              >
                <i class="fas {searchTerm ? 'fa-search' : 'fa-rotate-right'}"
                ></i>
              </button>
            </label>
          </form>
          <button
            on:click={handleCreate}
            class="btn btn-secondary btn-sm flex items-center gap-1"
            aria-label="Create new database"
          >
            <i class="fas fa-plus"></i>
            <span class="hidden md:inline">Create</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Separator line -->
    <div class="border-t border-base-content/10 mb-2"></div>

    <div class="flex-grow overflow-y-auto mb-4 relative">
      {#if loading}
        <div
          class="flex flex-col items-center justify-center h-full absolute inset-0 bg-base-100"
          in:fade={{ duration: 400 }}
          out:fade={{ duration: 400 }}
          aria-live="polite"
          aria-busy={loading}
        >
          <span
            class="loading loading-ring text-primary"
            style="width: 80px; height: 80px;"
          ></span>
          <!-- <p class="mt-8 text-2xl font-bold font-poppins text-secondary">
            Loading databases...
          </p> -->
        </div>
      {:else}
        <div
          class="transition-opacity duration-500 h-full"
          in:fade={{ duration: 400 }}
          out:fade={{ duration: 400 }}
        >
          {#if error}
            <div
              class="text-center text-error/40 h-full flex flex-col justify-center items-center"
            >
              <p class="text-2xl font-semibold poppins">
                Unable to load content
              </p>
            </div>
          {:else if databasesResponse.databases.length === 0}
            <div
              class="text-center text-error/60 h-full flex flex-col justify-center items-center"
            >
              <p class="text-2xl font-semibold poppins">
                No databases available
              </p>
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-1 p-1">
              {#each databasesResponse.databases as db, index (db)}
                {@const isLastRow =
                  index >= databasesResponse.databases.length - 4}
                {@const hasTooltip = overflowingDbs.has(db.name)}
                {@const dbKey = db.opaque_id ?? db.name}
                <div
                  class="card group shadow-sm h-14 hover:bg-neutral/20 transition-colors duration-200"
                >
                  <div
                    class="card-body px-2 py-1 flex-row justify-between items-center cursor-pointer"
                    on:click={() =>
                      handleDatabaseClick(db.opaque_id ?? db.name)}
                    role="button"
                    tabindex="0"
                    on:keydown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleDatabaseClick(db.opaque_id ?? db.name);
                      }
                    }}
                  >
                    <div
                      class="flex-1 mr-3 overflow-hidden {hasTooltip
                        ? `tooltip ${isLastRow ? 'tooltip-top' : 'tooltip-bottom'}`
                        : ''}"
                      data-tip={hasTooltip ? db.name : null}
                    >
                      <span
                        use:checkTextOverflow={db.name}
                        class="card-title text-base poppins font-normal transition-colors duration-200 block overflow-hidden text-ellipsis whitespace-nowrap"
                      >
                        {db.name}
                      </span>
                    </div>

                    <div
                      class="flex items-center gap-0.5 flex-shrink-0 relative"
                    >
                      <button
                        on:click|stopPropagation={() =>
                          toggleStats(db.name, db.opaque_id)}
                        class="tooltip tooltip-left hover:text-info px-2 rounded-full cursor-pointer"
                        data-tip="Show stats"
                        aria-label={`Show stats for ${db.name}`}
                      >
                        <i class="fas fa-chart-bar"></i>
                      </button>
                      <StatsPopover
                        showPopover={showStatsPopover === dbKey}
                        stats={dbStats[dbKey]}
                        loading={loadingStats[dbKey]}
                        rowIndex={index}
                        totalRows={databasesResponse.databases.length}
                        onClose={handleStatsClose}
                      />

                      <button
                        on:click|stopPropagation={() =>
                          copyDatabaseName(db.name)}
                        class="tooltip tooltip-left hover:text-primary px-2 rounded-full cursor-pointer"
                        data-tip="Copy"
                        aria-label={`Copy database name ${db.name}`}
                      >
                        <i
                          class="fa {justCopied === db.name
                            ? 'fa-solid'
                            : 'fa-regular'} fa-copy"
                        ></i>
                      </button>

                      <button
                        on:click|stopPropagation={() =>
                          handleDeleteClick(db.opaque_id ?? db.name, db.name)}
                        class="tooltip tooltip-left {isSystemDatabase(db.name)
                          ? 'text-base-content/30 cursor-not-allowed'
                          : 'hover:text-error cursor-pointer'} px-2 rounded-full"
                        data-tip={isSystemDatabase(db.name)
                          ? "Cannot delete system database"
                          : "Delete"}
                        aria-label={`Delete database ${db.name}`}
                        disabled={isSystemDatabase(db.name)}
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

    <!-- Pagination Controls -->
    <Pagination
      {currentPage}
      {totalPages}
      {loading}
      {pageSize}
      showPageSize={true}
      on:pageChange={handlePageChange}
      on:pageSizeChange={(e) => {
        pageSize = e.detail.pageSize;
        currentPage = 1;
        fetchDatabases();
      }}
    />
  </div>
</div>

<Modal
  title="Confirm Deletion"
  message={`Are you sure you want to delete the database "${dbToDeleteName}"? This action cannot be undone.`}
  onConfirm={confirmDelete}
  onCancel={cancelDelete}
  confirmButtonText="Delete"
  cancelButtonText="Cancel"
  show={showDeleteModal}
/>

<Modal
  title="Create New Database"
  message=""
  onConfirm={handleCreateDatabase}
  onCancel={() => {
    showCreateModal = false;
    newDbName = "";
    newCollectionName = "";
  }}
  confirmButtonText="Create"
  cancelButtonText="Cancel"
  confirmDisabled={!createFormValid}
  {validationMessage}
  show={showCreateModal}
>
  <div class="form-control mb-4">
    <label class="label" for="newDbName">
      <span class="label-text">Database Name</span>
    </label>
    <input
      type="text"
      id="newDbName"
      bind:value={newDbName}
      placeholder="Enter database name"
      class="input input-bordered w-full"
    />
  </div>
  <div class="form-control">
    <label class="label" for="newCollectionName">
      <span class="label-text flex items-center gap-2">
        Collection Name
        <div
          class="tooltip tooltip-right"
          data-tip="A collection name is required to create a database"
        >
          <i class="fas fa-info-circle text-accent text-sm cursor-help"></i>
        </div>
      </span>
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

  /* Custom tooltip styles for long database names */
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

  /* Stats card styling */
  .stat-card {
    background: rgba(var(--fallback-bc, 0 0 0), 0.05);
    border-radius: 0.375rem;
    padding: 0.5rem;
    text-align: center;
    border: 1px solid rgba(var(--fallback-bc, 0 0 0), 0.1);
  }

  .stat-card:hover {
    background: rgba(var(--fallback-bc, 0 0 0), 0.08);
  }
</style>
