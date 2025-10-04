<script lang="ts">
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { formatCount } from "$lib/stores/format";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedCollections } from "$lib/stores/types";
  import { fade } from "svelte/transition";

  export let db: string;
  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let loading: boolean = false;
  let error: boolean = false;

  const pageSize: number = 16;

  export let collectionsResponse: PaginatedCollections = {
    collections: [],
    total: 0,
    page: 1,
    page_size: 16,
  };

  let exportingCol: string | null = null;
  let showDeleteModal = false;
  let colToDelete: string | null = null;
  let showCreateModal = false;
  let newCollectionName: string = "";

  // Computed validation state for create collection
  $: createCollectionValid = newCollectionName.trim() !== "";
  $: collectionValidationMessage = !newCollectionName.trim()
    ? "Please fill in Collection Name"
    : "";

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

  /**
   * Navigates to the collection detail page.
   * @param collectionName The name of the collection to navigate to.
   */
  function handleCollectionClick(collectionName: string) {
    goto(`${base}/${db}/${collectionName}?type=collection`);
  }

  /**
   * Fetches the list of collections for the current database.
   */
  export async function fetchCollections() {
    loading = true;
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
    } catch (e) {
      error = true;
      collectionsResponse = {
        collections: [],
        total: 0,
        page: 1,
        page_size: pageSize,
      };
      addNotification(e instanceof Error ? e.message : String(e), "error");
    } finally {
      loading = false;
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
      addNotification(
        `Collection "${colToDelete}" deleted successfully.`,
        "success"
      );
      await fetchCollections();
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
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
   * Handles the creation of a new collection.
   */
  async function handleCreateCollection() {
    if (!createCollectionValid) return;

    try {
      await api.apiPost(`/db/${db}/col/${newCollectionName}`, {});
      addNotification(
        `Collection "${newCollectionName}" created successfully.`,
        "success"
      );
      showCreateModal = false;
      newCollectionName = "";
      currentPage = 1;
      await fetchCollections();
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Fetches collection data and triggers a download.
   */
  async function handleExport(colName: string) {
    exportingCol = colName;
    try {
      addNotification(`Exporting collection "${colName}"...`, "success");
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
      addNotification(e instanceof Error ? e.message : String(e), "error");
    } finally {
      exportingCol = null;
    }
  }
</script>

<div class="flex-grow overflow-y-auto pb-4 relative h-full">
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
          class="text-center text-secondary/40 h-full flex flex-col justify-center items-center"
        >
          <p class="text-2xl font-semibold poppins">No content available</p>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-1">
          {#each collectionsResponse.collections as collection, index (collection.collection_name)}
            {@const rowNumber = Math.floor(index / 2) + 1}
            {@const isLastRow = rowNumber === 8}
            {@const hasTooltip = overflowingCols.has(
              collection.collection_name
            )}
            <div
              class="card group shadow-lg cursor-pointer hover:bg-neutral/20 hover:shadow-xl transition-all duration-200 ease-in-out h-14 {hasTooltip
                ? `tooltip ${isLastRow ? 'tooltip-top' : 'tooltip-bottom'}`
                : ''}"
              data-tip={hasTooltip ? collection.collection_name : null}
              role="button"
              tabindex="0"
              on:click={() => handleCollectionClick(collection.collection_name)}
              on:keydown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleCollectionClick(collection.collection_name);
                }
              }}
              style="position: relative;"
            >
              <div class="card-body p-3 flex-row justify-between items-center">
                <div class="flex-1 mr-3 overflow-hidden" style="min-width: 0;">
                  <span
                    use:checkTextOverflow={collection.collection_name}
                    class="card-title text-l poppins font-normal block overflow-hidden text-ellipsis whitespace-nowrap"
                  >
                    {collection.collection_name}
                  </span>
                </div>
                <div class="flex items-center space-x-2 flex-shrink-0">
                  <div
                    class="text-accent text-xs font-medium flex items-center justify-center"
                  >
                    #{formatCount(collection.documents_count)}
                  </div>
                  <button
                    on:click|stopPropagation={() =>
                      handleExport(collection.collection_name)}
                    class="tooltip tooltip-left hover:text-secondary px-2 rounded-full cursor-pointer"
                    data-tip={`Export as JSON`}
                    aria-label={`Export collection ${collection.collection_name}`}
                    disabled={exportingCol === collection.collection_name}
                  >
                    {#if exportingCol === collection.collection_name}
                      <span class="loading loading-spinner loading-sm"></span>
                    {:else}
                      <i
                        class="fa-solid fa-arrow-up-right-from-square text-lg p-2 rounded-full"
                      ></i>
                    {/if}
                  </button>
                  <button
                    on:click|stopPropagation={() =>
                      handleDeleteClick(collection.collection_name)}
                    class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                    data-tip={`Delete`}
                    aria-label={`Delete collection ${collection.collection_name}`}
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
    message=""
    onConfirm={handleCreateCollection}
    onCancel={() => {
      showCreateModal = false;
      newCollectionName = "";
    }}
    confirmButtonText="Create"
    cancelButtonText="Cancel"
    confirmDisabled={!createCollectionValid}
    validationMessage={collectionValidationMessage}
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
        class="input input-bordered w-full input-secondary"
      />
    </div>
  </Modal>
{/if}

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
