<script lang="ts">
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import { page } from "$app/stores";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedCollections } from "$lib/stores/types";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";

  let { db } = $page.params;

  let collectionsResponse: PaginatedCollections = {
    collections: [],
    total: 0,
    page: 1,
    page_size: 16,
  };
  let loading = true;
  let exportingCol: string | null = null;

  // State for collection deletion modal
  let showDeleteModal = false;
  let colToDelete: string | null = null;

  // New state variables for the create collection modal
  let showCreateModal = false;
  let newCollectionName: string = "";

  // State for search and pagination
  let newSearchTerm: string = "";
  let searchTerm: string = "";
  let currentPage: number = 1;
  let pageInput: number = 1;
  const pageSize: number = 16;

  // Total number of pages for the pagination dropdown
  $: totalPages = Math.ceil(collectionsResponse.total / pageSize);

  /**
   * Fetches the list of collections for the current database.
   */
  async function fetchCollections() {
    loading = true;
    try {
      const query = new URLSearchParams();

      // Only add the 'search' parameter if a search term has been entered.
      if (searchTerm.trim() !== "") {
        query.append("search", searchTerm);
      }

      // Pagination parameters are always included for UI functionality.
      query.append("page", currentPage.toString());
      query.append("page_size", pageSize.toString());

      const response = await api.apiGet<PaginatedCollections>(
        `/db/${db}/col?${query.toString()}`
      );
      collectionsResponse = response;
      pageInput = currentPage; // Keep the input in sync with the current page
    } catch (e) {
      addNotification("Failed to fetch collections.", "error");
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
    fetchCollections();
  }

  /**
   * Navigates to the document view for a specific collection.
   * @param collectionName The name of the collection to navigate to.
   */
  function handleCollectionClick(collectionName: string) {
    goto(base + `/${db}/${collectionName}`);
  }

  /**
   * Sets up the deletion confirmation modal.
   * @param col The name of the collection to delete.
   */
  function handleDeleteClick(col: string) {
    showDeleteModal = true;
    colToDelete = col;
  }

  /**
   * Clears the search input and triggers a new fetch.
   */
  function clearSearch() {
    newSearchTerm = "";
    handleSearch();
  }

  /**
   * Confirms and performs the collection deletion.
   */
  async function confirmDelete() {
    if (!colToDelete) return;
    try {
      await api.apiDelete(`/db/${db}/col/${colToDelete}`);
      addNotification(
        `Collection "${colToDelete}" deleted successfully.`,
        "success"
      );
      await fetchCollections();
    } catch (e) {
      addNotification(`Failed to delete collection: ${colToDelete}.`, "error");
      console.error(e);
    } finally {
      showDeleteModal = false;
      colToDelete = null;
    }
  }

  /**
   * Cancels the collection deletion.
   */
  function cancelDelete() {
    showDeleteModal = false;
    colToDelete = null;
  }

  /**
   * Handles the click on the "Create Collection" button.
   */
  function handleCreateClick() {
    showCreateModal = true;
  }

  /**
   * Handles the creation of a new collection.
   */
  async function handleCreateCollection() {
    if (!newCollectionName.trim()) {
      addNotification("Collection name cannot be empty.", "error");
      return;
    }
    try {
      // API call to create a new collection using the provided endpoint
      await api.apiPost(`/db/${db}/col/${newCollectionName}`, {});
      addNotification(
        `Collection "${newCollectionName}" created successfully.`,
        "success"
      );
      showCreateModal = false;
      newCollectionName = ""; // Clear the input
      currentPage = 1; // Go back to the first page to see the new collection
      await fetchCollections();
    } catch (e) {
      addNotification(
        `Failed to create collection: ${newCollectionName}.`,
        "error"
      );
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
      fetchCollections();
    }
  }

  /**
   * Navigates to the next page of collections.
   */
  function handleNextPage() {
    if (currentPage < totalPages) {
      currentPage++;
      fetchCollections();
    }
  }

  /**
   * Navigates to the previous page of collections.
   */
  function handlePrevPage() {
    if (currentPage > 1) {
      currentPage--;
      fetchCollections();
    }
  }

  /**
   * Navigates to the first page of collections.
   */
  function handleFirstPage() {
    if (currentPage !== 1) {
      currentPage = 1;
      fetchCollections();
    }
  }

  /**
   * Navigates to the last page of collections.
   */
  function handleLastPage() {
    if (currentPage !== totalPages) {
      currentPage = totalPages;
      fetchCollections();
    }
  }

  /**
   * Fetches the collection data and triggers a download of a JSON file.
   * @param colName The name of the collection to export.
   */
  async function handleExport(colName: string) {
    exportingCol = colName; // Set the state to show loading spinner
    try {
      addNotification(`Exporting collection "${colName}"...`, "info");
      const response = await api.apiGet<any>(`/db/${db}/col/${colName}/export`);

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
      addNotification(`Failed to export collection: ${colName}.`, "error");
      console.error(e);
    } finally {
      exportingCol = null; // Reset the state regardless of success or failure
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    fetchCollections();
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
      <Breadcrumb
        showBackButton={true}
        segments={[
          { name: "Home", isHome: true, href: "/" },
          { name: db || "", href: `/${db}`, label: "Database" },
        ]}
      />
      <h1 class="text-3xl poppins mb-3 mt-3 text-center">
        <i class="fa-solid fa-layer-group text-primary"></i>
        Collections
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
              placeholder="Search collection..."
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
          data-tip="Create new collection"
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
            Loading collections...
          </p>
        </div>
      {:else}
        <div
          class="transition-opacity duration-500"
          in:fade={{ duration: 400 }}
          out:fade={{ duration: 400 }}
        >
          {#if collectionsResponse.collections.length === 0}
            <div
              class="text-center text-secondary h-full flex flex-col justify-center"
            >
              <p class="text-xl font-semibold poppins">No collections found</p>
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-1">
              {#each collectionsResponse.collections as col (col)}
                <div
                  class="card group shadow-lg bg-base-200 cursor-pointer hover:bg-accent/20 hover:shadow-xl transition-all duration-200 ease-in-out"
                  on:click={() => handleCollectionClick(col)}
                >
                  <div
                    class="card-body p-3 flex-row justify-between items-center"
                  >
                    <span
                      class="card-title text-l poppins font-normal group-hover:text-accent"
                    >
                      {col}
                    </span>
                    <div class="flex items-center space-x-2">
                      <button
                        on:click|stopPropagation={() => handleExport(col)}
                        class="tooltip tooltip-left hover:text-secondary px-2 rounded-full cursor-pointer"
                        data-tip={`Export as JSON`}
                        aria-label={`Export collection ${col}`}
                        disabled={exportingCol === col}
                      >
                        {#if exportingCol === col}
                          <span class="loading loading-spinner loading-sm"
                          ></span>
                        {:else}
                          <i
                            class="fa-solid fa-arrow-up-right-from-square text-lg p-2 rounded-full"
                          ></i>
                        {/if}
                      </button>
                      <button
                        on:click|stopPropagation={() => handleDeleteClick(col)}
                        class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                        data-tip={`Delete`}
                        aria-label={`Delete collection ${col}`}
                      >
                        <i class="fas fa-trash-alt text-lg"></i>
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

    <div class="mt-4">
      <div
        class="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0"
      >
        <div class="text-sm text-secondary">
          Displaying {collectionsResponse.collections.length ===
          collectionsResponse.total
            ? "all"
            : `${(currentPage - 1) * pageSize + 1} - ${Math.min(currentPage * pageSize, collectionsResponse.total)}`}
          of {collectionsResponse.total}
          collections
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
              class="input input-sm w-16 text-center"
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
    message={`Are you sure you want to delete the collection "${colToDelete}"? This action cannot be undone.`}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}

{#if showCreateModal}
  <Modal
    title="Create New Collection"
    onConfirm={handleCreateCollection}
    onCancel={() => {
      showCreateModal = false;
      newCollectionName = "";
    }}
    confirmButtonText="Create"
    cancelButtonText="Cancel"
    confirmDisabled={!newCollectionName.trim()}
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
{/if}

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }
</style>
