<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedDatabases } from "$lib/stores/types";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";

  let databasesResponse: PaginatedDatabases = {
    databases: [],
    total: 0,
    page: 1,
    page_size: 16,
  };
  let loading = true;
  let showDeleteModal = false;
  let dbToDelete: string | null = null;
  let showCreateModal = false;
  let newDbName: string = "";
  let newCollectionName: string = "";

  // Search and pagination state
  let searchTerm: string = "";
  let currentPage: number = 1;
  const pageSize: number = 16;
  $: totalPages = Math.ceil(databasesResponse.total / pageSize);

  // Track which database names are overflowing
  let overflowingDbs = new Set<string>();

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

  // Computed validation state
  $: createFormValid =
    newDbName.trim() !== "" && newCollectionName.trim() !== "";
  $: validationMessage =
    !newDbName.trim() && !newCollectionName.trim()
      ? "Please fill in Database Name and Collection Name"
      : !newDbName.trim()
        ? "Please fill in Database Name"
        : !newCollectionName.trim()
          ? "Please fill in Collection Name"
          : "";

  /**
   * Fetches the list of databases.
   */
  async function fetchDatabases() {
    loading = true;
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
      addNotification(e.message, "error");
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
   * @param db The name of the database to navigate to.
   */
  function handleDatabaseClick(db: string) {
    goto(resolve(`/${db}`));
  }

  /**
   * Sets up the deletion confirmation modal.
   * @param db The name of the database to delete.
   */
  function handleDeleteClick(db: string) {
    showDeleteModal = true;
    dbToDelete = db;
  }

  /**
   * Confirms and performs the database deletion.
   */
  async function confirmDelete() {
    if (!dbToDelete) return;
    try {
      await api.apiDelete(`/db/${dbToDelete}`);
      addNotification(
        `Database "${dbToDelete}" deleted successfully.`,
        "success"
      );
      await fetchDatabases();
    } catch (e) {
      addNotification(e.message, "error");
      // addNotification(`Failed to delete database: ${dbToDelete}.`, "error");
    } finally {
      showDeleteModal = false;
      dbToDelete = null;
    }
  }

  /**
   * Cancels the database deletion.
   */
  function cancelDelete() {
    showDeleteModal = false;
    dbToDelete = null;
  }

  /**
   * Handles the click on the "Create Database" button.
   */
  function handleCreateClick() {
    showCreateModal = true;
  }

  /**
   * Handles the creation of a new database.
   */
  async function handleCreateDatabase() {
    if (!createFormValid) return;

    try {
      await api.apiPost(
        `/db/${newDbName}?collection_name=${newCollectionName}`,
        {}
      );
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
      addNotification(e.message, "error");
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    fetchDatabases();
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
      <h1 class="text-3xl poppins mb-3 mt-3 text-center">
        <i class="fas fa-database mr-2 text-primary"></i>
        Databases
      </h1>
      <Breadcrumb segments={[{ name: "Home", isHome: true, href: "/" }]} />

      <!-- Search and Create Controls -->
      <div
        class="flex flex-col md:flex-row justify-between items-center mb-4 space-y-2 md:space-y-0"
      >
        <form
          on:submit|preventDefault={() =>
            handleSearch({ detail: { term: searchTerm } })}
          class="relative w-full md:w-1/3 flex"
        >
          <label
            class="input input-bordered input-secondary flex items-center gap-2 w-full"
          >
            <input
              type="text"
              class="grow"
              bind:value={searchTerm}
              placeholder="Search database..."
            />
            {#if searchTerm}
              <button
                type="button"
                on:click={() => {
                  searchTerm = "";
                  handleSearch({ detail: { term: "" } });
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
          aria-label="Create new database"
          data-tip="Create new database"
        >
          <i class="fas fa-plus mr-0"></i>
        </button>
      </div>
    </div>

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
          <p class="mt-8 text-2xl font-bold font-poppins text-secondary">
            Loading databases...
          </p>
        </div>
      {:else}
        <div
          class="transition-opacity duration-500 h-full"
          in:fade={{ duration: 400 }}
          out:fade={{ duration: 400 }}
        >
          {#if databasesResponse.databases.length === 0}
            <div
              class="text-center text-secondary h-full flex flex-col justify-center items-center"
            >
              <p class="text-xl font-semibold poppins">No databases found</p>
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-1">
              {#each databasesResponse.databases as db, index (db)}
                {@const rowNumber = Math.floor(index / 2) + 1}
                {@const isLastRow = rowNumber === 8}
                {@const hasTooltip = overflowingDbs.has(db)}
                <div
                  class="card group shadow-lg cursor-pointer hover:bg-accent/20 hover:shadow-xl transition-all duration-200 ease-in-out h-14 {hasTooltip
                    ? `tooltip ${isLastRow ? 'tooltip-top' : 'tooltip-bottom'}`
                    : ''}"
                  data-tip={hasTooltip ? db : null}
                  on:click={() => handleDatabaseClick(db)}
                  style="position: relative;"
                >
                  <div
                    class="card-body p-3 flex-row justify-between items-center"
                  >
                    <div
                      class="flex-1 mr-3 overflow-hidden"
                      style="min-width: 0;"
                    >
                      <span
                        use:checkTextOverflow={db}
                        class="card-title text-l poppins font-normal transition-colors duration-200 block overflow-hidden text-ellipsis whitespace-nowrap"
                      >
                        {db}
                      </span>
                    </div>

                    <button
                      on:click|stopPropagation={() => handleDeleteClick(db)}
                      class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer flex-shrink-0"
                      data-tip="Delete"
                      aria-label={`Delete database ${db}`}
                    >
                      <i class="fas fa-trash-alt text-lg"></i>
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Pagination Controls -->
    <div
      class="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0"
    >
      <div class="text-sm text-secondary">
        Displaying {databasesResponse.databases.length ===
        databasesResponse.total
          ? "all"
          : `${(currentPage - 1) * pageSize + 1} - ${Math.min(currentPage * pageSize, databasesResponse.total)}`}
        of {databasesResponse.total} databases
      </div>
      <div class="join">
        <button
          on:click={() => handlePageChange({ detail: { page: 1 } })}
          disabled={currentPage === 1 || loading}
          class="join-item btn hover:text-accent/80"
          aria-label="First page"
        >
          «
        </button>
        <button
          on:click={() =>
            handlePageChange({ detail: { page: currentPage - 1 } })}
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
            on:change={() => fetchDatabases()}
            min="1"
            max={totalPages}
            class="input input-sm w-16 text-center input-neutral"
          />
          <span class="text-base-content">of {totalPages}</span>
        </div>
        <button
          on:click={() =>
            handlePageChange({ detail: { page: currentPage + 1 } })}
          disabled={currentPage >= totalPages || loading}
          class="join-item btn hover:text-accent/80"
          aria-label="Next page"
        >
          ›
        </button>
        <button
          on:click={() => handlePageChange({ detail: { page: totalPages } })}
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

{#if showDeleteModal}
  <Modal
    title="Confirm Deletion"
    message={`Are you sure you want to delete the database "${dbToDelete}"? This action cannot be undone.`}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}

{#if showCreateModal}
  <Modal
    title="Create New Database"
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
        class="input input-bordered w-full input-secondary"
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
        class="input input-bordered w-full input-secondary"
      />
    </div>
  </Modal>
{/if}

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
</style>
