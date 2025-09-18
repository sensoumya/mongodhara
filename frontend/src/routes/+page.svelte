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
  let newSearchTerm: string = "";
  let searchTerm: string = "";
  let currentPage: number = 1;
  let pageInput: number = 1;
  const pageSize: number = 16;
  $: totalPages = Math.ceil(databasesResponse.total / pageSize);

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
      pageInput = currentPage;
    } catch (e) {
      addNotification("Failed to fetch databases.", "error");
      console.error(e);
    } finally {
      loading = false;
    }
  }

  /**
   * Handles the search button click, resetting the page to 1.
   */
  function handleSearch() {
    currentPage = 1;
    searchTerm = newSearchTerm;
    fetchDatabases();
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
      addNotification(`Failed to delete database: ${dbToDelete}.`, "error");
      console.error(e);
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
    if (!newDbName.trim()) {
      addNotification("Database name cannot be empty.", "error");
      return;
    }
    try {
      await api.apiPost(`/db/${newDbName}`, {});
      addNotification(
        `Database "${newDbName}" created successfully.`,
        "success"
      );
      showCreateModal = false;
      newDbName = ""; // Clear the input
      currentPage = 1; // Go back to the first page to see the new database
      await fetchDatabases();
    } catch (e) {
      addNotification(`Failed to create database: ${newDbName}.`, "error");
      console.error(e);
    }
  }

  /**
   * Handles the change event for the page input field.
   * @param event The DOM event.
   */
  function handlePageInput(event: Event) {
    const value = parseInt((event.target as HTMLInputElement).value, 10);
    if (!isNaN(value) && value > 0 && value <= totalPages) {
      currentPage = value;
      fetchDatabases();
    }
  }

  /**
   * Navigates to the next page of databases.
   */
  function handleNextPage() {
    if (currentPage < totalPages) {
      currentPage++;
      fetchDatabases();
    }
  }

  /**
   * Navigates to the previous page of databases.
   */
  function handlePrevPage() {
    if (currentPage > 1) {
      currentPage--;
      fetchDatabases();
    }
  }

  /**
   * Navigates to the first page of databases.
   */
  function handleFirstPage() {
    if (currentPage !== 1) {
      currentPage = 1;
      fetchDatabases();
    }
  }

  /**
   * Clears the search input and triggers a new fetch.
   */
  function clearSearch() {
    newSearchTerm = "";
    handleSearch();
  }

  /**
   * Navigates to the last page of databases.
   */
  function handleLastPage() {
    if (currentPage !== totalPages) {
      currentPage = totalPages;
      fetchDatabases();
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
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"
    integrity="sha512-SnH5WK+bZxgPHs44uW/r8W7Wj8n4Lz8mY9wA4164w2r86Lz8mFj+J/l+Y/sD+8L/LqN+g96N+A=="
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
      <Breadcrumb segments={[{ name: "Home", isHome: true, href: "/" }]} />
      <h1 class="text-3xl poppins mb-3 mt-3 text-center">
        <i class="fas fa-database mr-2 text-primary"></i>
        Databases
      </h1>
      <div
        class="flex flex-col md:flex-row justify-between items-center mb-2 space-y-2 md:space-y-0"
      >
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
              placeholder="Search database..."
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
                ><path
                  fill-rule="evenodd"
                  d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.094 2.093a.75.75 0 0 1-1.06 1.06l-2.094-2.094ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
                  clip-rule="evenodd"
                /></svg
              >
            </button>
          </label>
        </form>
        <button
          on:click={handleCreateClick}
          class="btn btn-secondary px-4 py-3 rounded-md transition-colors duration-300 tooltip"
          aria-label="Create new database"
          data-tip="Create new database"
        >
          <i class="fas fa-plus mr-0"></i>
        </button>
      </div>
    </div>

    <div class="flex-grow overflow-y-auto pb-4 relative">
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
          class="transition-opacity duration-500"
          in:fade={{ duration: 400 }}
          out:fade={{ duration: 400 }}
        >
          {#if databasesResponse.databases.length === 0}
            <div class="text-center h-full flex flex-col justify-center">
              <p class="text-xl font-semibold poppins text-secondary">
                No databases found.
              </p>
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-1">
              {#each databasesResponse.databases as db (db)}
                <div
                  class="card group shadow-lg bg-base-200 cursor-pointer hover:bg-accent/20 hover:shadow-xl transition-all duration-200 ease-in-out"
                  on:click={() => handleDatabaseClick(db)}
                >
                  <div
                    class="card-body p-3 flex-row justify-between items-center"
                  >
                    <span
                      class="card-title text-l poppins font-normal transition-colors duration-200 group-hover:text-accent"
                    >
                      {db}
                    </span>

                    <button
                      on:click|stopPropagation={() => handleDeleteClick(db)}
                      class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                      data-tip={`Delete`}
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

    <div class="mt-4">
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
              class="input input-sm w-16 text-center input-neutral"
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
    }}
    confirmButtonText="Create"
    cancelButtonText="Cancel"
    confirmDisabled={!newDbName.trim()}
  >
    <div class="form-control">
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
  </Modal>
{/if}

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }
</style>
