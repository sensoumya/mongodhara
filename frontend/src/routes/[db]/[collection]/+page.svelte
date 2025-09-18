<script lang="ts">
  import { page } from "$app/stores";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import JsonEditor from "$lib/components/JsonEditor.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedDocuments } from "$lib/stores/types";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";

  // SvelteKit store to get URL parameters
  let { db, collection } = $page.params;

  // State for documents and pagination
  let documentsResponse: PaginatedDocuments = {
    docs: [],
    total: 0,
    page: 1,
    page_size: 16, // Consistent page size
  };
  let loading = true;
  let isTableLoading = false; // New state variable for table loading

  // State for document deletion modal
  let showDeleteModal = false;
  let docToDelete: string | null = null;
  let hoveredRowId: string | null = null; // New state for hover

  // New state variables for the JSON editor sidebar and query popup
  let showEditorSidebar = false;
  let documentToEdit: any | null = null;
  let isQueryMaximized = false; // New state variable for in-place expansion
  let validationError: string | null = null;

  // State for search/query, pagination, and sorting
  let queryTerm: string = "";
  let currentPage: number = 1;
  let pageInput: number = 1; // New state for the page input field
  const pageSize: number = 12;
  // Total number of pages for the pagination dropdown
  $: totalPages = Math.ceil(documentsResponse.total / pageSize);

  // New state variables for sorting, initialized to null so they are not sent by default
  let sortField: string | null = null;
  let sortOrder: 1 | -1 | null = null;

  // List of all unique keys from all documents for the table headers
  let allKeys: string[] = [];
  const maxLength = 50;

  // References to the table bodies for height synchronization
  let mainTableBody: HTMLTableSectionElement;
  let actionTableBody: HTMLTableSectionElement;

  /**
   * Truncates a string to a maximum length and adds an ellipsis.
   * @param str The string to truncate.
   * @param maxLen The maximum length of the string.
   * @returns The truncated string.
   */
  function truncateString(str: string, maxLen: number): string {
    if (str && str.length > maxLen) {
      return str.substring(0, maxLen) + "...";
    }
    return str;
  }

  /**
   * Extracts and sorts all unique keys from a list of documents based on a specific order.
   * - _id is always first.
   * - Then, columns with 'id' in their name (case-insensitive), sorted alphabetically.
   * - Then, columns with 'name' in their name (case-insensitive), sorted alphabetically.
   * - Finally, all other columns, sorted alphabetically.
   * @param docs An array of document objects.
   * @returns An array of unique, sorted keys.
   */
  function extractAllKeys(docs: any[]): string[] {
    const allUniqueKeys = new Set<string>();
    docs.forEach((doc) => {
      Object.keys(doc).forEach((key) => {
        allUniqueKeys.add(key);
      });
    });

    // Separate keys into categories
    const idKeys: string[] = [];
    const nameKeys: string[] = [];
    const otherKeys: string[] = [];

    allUniqueKeys.forEach((key) => {
      if (key === "_id") {
        // _id will be added explicitly later
        return;
      }
      const lowerCaseKey = key.toLowerCase();
      if (lowerCaseKey.includes("id")) {
        idKeys.push(key);
      } else if (lowerCaseKey.includes("name")) {
        nameKeys.push(key);
      } else {
        otherKeys.push(key);
      }
    });

    // Sort each category alphabetically
    idKeys.sort();
    nameKeys.sort();
    otherKeys.sort();

    // Construct the final sorted array
    return ["_id", ...idKeys, ...nameKeys, ...otherKeys];
  }

  // Reactive block to perform live validation of the JSON query
  $: {
    if (isQueryMaximized && queryTerm.trim() !== "") {
      try {
        JSON.parse(queryTerm);
        validationError = null;
      } catch (e: any) {
        validationError = e.message;
      }
    } else {
      validationError = null;
    }
  }

  // Reactive block to synchronize row heights
  $: {
    // Only run if both table bodies exist and documents are loaded
    if (mainTableBody && actionTableBody && documentsResponse.docs.length > 0) {
      requestAnimationFrame(() => {
        const mainRows = mainTableBody.querySelectorAll("tr");
        const actionRows = actionTableBody.querySelectorAll("tr");

        // Check if the number of rows matches to prevent errors
        if (mainRows.length !== actionRows.length) {
          // This can happen if the DOM is still updating. We'll wait for the next frame.
          return;
        }

        mainRows.forEach((mainRow, index) => {
          if (actionRows[index]) {
            actionRows[index].style.height = `${mainRow.offsetHeight}px`;
          }
        });
      });
    }
  }

  /**
   * Formats the JSON query string with indentation.
   */
  function handleBeautify() {
    if (!validationError && queryTerm.trim() !== "") {
      try {
        const parsed = JSON.parse(queryTerm);
        queryTerm = JSON.stringify(parsed, null, 2);
      } catch (e) {
        // Validation error is already handled by the reactive block
      }
    }
  }

  /**
   * Fetches documents from the server with pagination, sorting, and filtering.
   * @param isInitialLoad Boolean to indicate if this is the first fetch on mount.
   */
  async function fetchDocuments(isInitialLoad: boolean = false) {
    if (!collection) {
      console.error("Collection parameter is missing. Cannot fetch documents.");
      loading = false;
      return;
    }

    if (isInitialLoad) {
      loading = true;
    } else {
      isTableLoading = true;
    }

    try {
      // Construct query parameters
      const queryParams = new URLSearchParams();
      queryParams.append("page", currentPage.toString());
      queryParams.append("page_size", pageSize.toString());

      // Only add sort parameters if they have been set by the user
      if (sortField !== null && sortOrder !== null) {
        queryParams.append("sort_field", sortField);
        queryParams.append("sort_order", sortOrder.toString());
      }

      let parsedQuery = {};
      let hasQuery = false;
      if (queryTerm.trim() !== "") {
        try {
          parsedQuery = JSON.parse(queryTerm);
          if (Object.keys(parsedQuery).length > 0) {
            hasQuery = true;
          }
        } catch (e) {
          addNotification("Invalid JSON query.", "error");
          loading = false;
          isTableLoading = false;
          return;
        }
      }

      const body = {
        filter: hasQuery ? parsedQuery : {},
      };

      console.log("Fetching documents with:", {
        filter: body.filter,
        sortField,
        sortOrder,
        currentPage,
        pageSize,
      });

      const response = await api.apiPost<PaginatedDocuments>(
        `/db/${db}/col/${collection}/doc/query?${queryParams.toString()}`,
        body
      );
      if (response && response.data) {
        documentsResponse = {
          docs: response.data,
          total: response.total,
          page: response.page,
          page_size: response.page_size,
        };
      } else {
        documentsResponse = {
          docs: [],
          total: 0,
          page: 1,
          page_size: pageSize,
        };
        addNotification("Invalid API response received.", "error");
      }
      allKeys = extractAllKeys(documentsResponse.docs);
      pageInput = currentPage;
    } catch (e) {
      addNotification("Failed to fetch documents.", "error");
      console.error(e);
      documentsResponse = {
        docs: [],
        total: 0,
        page: 1,
        page_size: pageSize,
      };
    } finally {
      loading = false;
      isTableLoading = false;
    }
  }

  /**
   * Handles the search button click, resetting the page to 1.
   */
  function handleSearch() {
    currentPage = 1;
    fetchDocuments();
  }

  /**
   * Handles clicking on a table header to sort by that field.
   * @param key The field to sort by.
   */
  function handleHeaderSort(key: string) {
    // If the same field is clicked, toggle the sort order
    if (sortField === key) {
      sortOrder = sortOrder === 1 ? -1 : 1;
    } else {
      // If a new field is clicked, set it and default to ascending order
      sortField = key;
      sortOrder = 1;
    }
    currentPage = 1; // Reset to the first page when sorting
    fetchDocuments();
  }

  /**
   * Sets up the deletion confirmation modal.
   * @param doc The document to delete.
   */
  function handleDeleteClick(doc: any) {
    showDeleteModal = true;
    docToDelete = doc._id;
  }

  /**
   * Confirms and performs the document deletion.
   */
  async function confirmDelete() {
    if (!docToDelete) return;
    try {
      await api.apiDelete(`/db/${db}/col/${collection}/doc/${docToDelete}`);
      addNotification(
        `Document with ID "${docToDelete}" deleted successfully.`,
        "success"
      );
      await fetchDocuments();
    } catch (e) {
      addNotification(`Failed to delete document: ${docToDelete}.`, "error");
      console.error(e);
    } finally {
      showDeleteModal = false;
      docToDelete = null;
    }
  }

  /**
   * Cancels the document deletion.
   */
  function cancelDelete() {
    showDeleteModal = false;
    docToDelete = null;
  }

  // Handle direct page input
  function handlePageInput(event: Event) {
    const value = parseInt((event.target as HTMLInputElement).value, 10);
    if (!isNaN(value) && value > 0 && value <= totalPages) {
      currentPage = value;
      fetchDocuments();
    } else {
      addNotification("Invalid page number.", "error");
    }
  }

  // Handle next page
  function handleNextPage() {
    if (currentPage < totalPages) {
      currentPage++;
      fetchDocuments();
    }
  }

  // Handle previous page
  function handlePrevPage() {
    if (currentPage > 1) {
      currentPage--;
      fetchDocuments();
    }
  }

  // Handle first page
  function handleFirstPage() {
    if (currentPage !== 1) {
      currentPage = 1;
      fetchDocuments();
    }
  }

  // Handle last page
  function handleLastPage() {
    if (currentPage !== totalPages) {
      currentPage = totalPages;
      fetchDocuments();
    }
  }

  /**
   * Opens the JSON editor sidebar with the selected document.
   * @param doc The document to edit.
   */
  function handleRowClick(doc: object) {
    documentToEdit = doc;
    showEditorSidebar = true;
  }

  /**
   * Handles the click of the "Add Document" button to open the editor
   * in creation mode.
   */
  function handleNewDocumentClick() {
    documentToEdit = {}; // Initialize with an empty object for a new document
    showEditorSidebar = true;
  }

  /**
   * Handles the saving of a document from the JsonEditor.
   * This function now handles both creation (POST) and updating (PUT).
   * @param updatedDoc The document with the updated fields.
   */
  async function handleSave(event: CustomEvent) {
    const updatedDoc = event.detail;
    try {
      if (!updatedDoc._id) {
        // Use api.apiPost for creating new documents
        delete updatedDoc._id; // Ensure _id is not sent for a new document
        await api.apiPost(`/db/${db}/col/${collection}/doc`, {
          data: updatedDoc,
        });
        addNotification("New document created successfully.", "success");
      } else {
        // Use api.apiPut for updating existing documents
        await api.apiPut(`/db/${db}/col/${collection}/doc/${updatedDoc._id}`, {
          data: updatedDoc,
        });
        addNotification("Document updated successfully.", "success");
      }

      showEditorSidebar = false;
      await fetchDocuments();
    } catch (e) {
      addNotification(
        "Failed to save document. Please check the data format.",
        "error"
      );
      console.error(e);
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    fetchDocuments(true);
  });
</script>

<svelte:head>
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"
    xintegrity="sha512-SnH5WK+bZxgPHs44uW/r8W7Wj8n4Lz8mY9wA4164w2r86Lz8mFj+J/l+Y/sD+8L/LqN+g96N+A=="
    crossorigin="anonymous"
    referrerpolicy="origin"
  />
</svelte:head>

<div
  class="h-[calc(100vh-90px)] flex flex-col p-2 md:p-4 text-base-content"
  in:fade={{ duration: 200 }}
  out:fade={{ duration: 200 }}
>
  <div class="max-w-7xl mx-auto w-full h-full flex flex-col">
    <div class="mb-4">
      <Breadcrumb
        showBackButton={true}
        segments={[
          { name: "Home", isHome: true, href: "/" },
          { name: db, href: `/${db}`, label: "Database" },
          { name: collection, label: "Collection" },
        ]}
      />

      <h1 class="text-3xl poppins mb-3 mt-3 text-center">
        <i class="fas fa-file-alt text-primary"></i>
        Documents
      </h1>

      <div
        class="flex flex-col md:flex-row justify-between items-center mb-4 space-y-2 md:space-y-0"
      >
        <div class="relative w-full md:w-1/3 query-container">
          <form on:submit|preventDefault={handleSearch} class="relative">
            <!-- Collapsed state -->
            <label
              class="input input-bordered input-secondary flex items-center gap-2 w-full"
              class:hidden={isQueryMaximized}
            >
              <input
                type="text"
                class="grow"
                bind:value={queryTerm}
                placeholder="Enter JSON query..."
              />
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
              <button
                type="button"
                on:click={() => (isQueryMaximized = true)}
                class="btn btn-sm btn-ghost"
                aria-label="Expand query input"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"
                  />
                </svg>
              </button>
            </label>

            <!-- Expanded state -->
            <div
              class="query-expanded-overlay absolute top-0 left-0 w-full bg-base-100 rounded-lg shadow-xl z-50 border-2 border-secondary"
              class:hidden={!isQueryMaximized}
              in:fade={{ duration: 200 }}
              out:fade={{ duration: 200 }}
            >
              <div class="relative p-4">
                <textarea
                  bind:value={queryTerm}
                  class="textarea w-full h-96 font-mono text-sm resize-none border-none focus:outline-none bg-transparent"
                  placeholder="Enter JSON query..."
                ></textarea>
                {#if validationError}
                  <div class="text-sm text-error mt-2">
                    Error: {validationError}
                  </div>
                {/if}
                <div class="absolute bottom-4 right-4 flex items-center gap-2">
                  <button
                    type="button"
                    on:click={handleBeautify}
                    class="btn btn-sm btn-base-100"
                    disabled={!!validationError}
                    aria-label="Beautify JSON"
                  >
                    <i class="fas fa-wand-magic-sparkles"></i>
                  </button>
                  <button
                    type="submit"
                    class="btn btn-sm btn-base-100"
                    disabled={!!validationError}
                    aria-label="Search"
                  >
                    <i class="fas fa-search"></i>
                  </button>
                  <button
                    type="button"
                    on:click={() => (isQueryMaximized = false)}
                    class="btn btn-sm btn-base-100"
                    aria-label="Compress query input"
                  >
                    <i class="fas fa-compress"></i>
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>
        <button
          on:click={handleNewDocumentClick}
          class="btn btn-secondary px-4 py-3 rounded-md transition-colors duration-300 tooltip"
          data-tip="Add new document"
        >
          <i class="fas fa-plus mr-0"></i>
        </button>
      </div>
    </div>

    <div
      class="flex-grow overflow-y-auto table-container rounded-box relative shadow-2xl"
    >
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
            Loading documents...
          </p>
        </div>
      {:else if documentsResponse.docs.length === 0}
        <div
          class="text-center text-secondary h-full flex flex-col justify-center"
        >
          <p class="text-xl font-semibold poppins">No documents found.</p>
        </div>
      {:else}
        <div class="flex relative">
          <div
            class="overflow-x-auto flex-grow transition-opacity duration-300"
            class:opacity-50={isTableLoading}
          >
            <table class="table w-full text-left">
              <thead>
                <tr class="bg-primary/40">
                  {#each allKeys as key}
                    <th
                      class="cursor-pointer"
                      on:click={() => handleHeaderSort(key)}
                    >
                      <div class="flex items-center poppins space-x-1">
                        <span>{key}</span>
                        {#if sortField === key}
                          {#if sortOrder === 1}
                            <i class="fas fa-arrow-up text-xs"></i>
                          {:else}
                            <i class="fas fa-arrow-down text-xs"></i>
                          {/if}
                        {/if}
                      </div>
                    </th>
                  {/each}
                </tr>
              </thead>
              <tbody bind:this={mainTableBody}>
                {#each documentsResponse.docs as doc (doc._id)}
                  <tr
                    in:fade={{ duration: 200 }}
                    out:fade={{ duration: 200 }}
                    on:click={() => handleRowClick(doc)}
                    on:mouseenter={() => (hoveredRowId = doc._id)}
                    on:mouseleave={() => (hoveredRowId = null)}
                    class="cursor-pointer transition-colors duration-150 {hoveredRowId ===
                    doc._id
                      ? 'bg-accent/10 text-accent font-bold'
                      : 'hover:bg-accent/10'}"
                  >
                    {#each allKeys as key}
                      <td
                        class="max-w-xs overflow-hidden text-ellipsis whitespace-nowrap roboto"
                      >
                        {#if typeof doc[key] === "object" && doc[key] !== null}
                          <span class="font-mono">
                            {truncateString(
                              JSON.stringify(doc[key]),
                              maxLength
                            )}
                          </span>
                        {:else}
                          <span>
                            {truncateString(doc[key] || "null", maxLength)}
                          </span>
                        {/if}
                      </td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <div
            class="flex-none transition-opacity duration-300"
            class:opacity-50={isTableLoading}
          >
            <table class="table w-full">
              <thead>
                <tr class="bg-primary/40 poppins">
                  <th class="text-center">Actions</th>
                </tr>
              </thead>
              <tbody bind:this={actionTableBody}>
                {#each documentsResponse.docs as doc (doc._id)}
                  <tr
                    in:fade={{ duration: 200 }}
                    out:fade={{ duration: 200 }}
                    on:mouseenter={() => (hoveredRowId = doc._id)}
                    on:mouseleave={() => (hoveredRowId = null)}
                    class="transition-colors duration-150 {hoveredRowId ===
                    doc._id
                      ? 'bg-accent/10'
                      : 'hover:bg-accent/10'}"
                  >
                    <td class="text-center no-padding-table-cell">
                      <button
                        on:click|stopPropagation={() => handleDeleteClick(doc)}
                        class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                        data-tip={`Delete document with ID: ${doc._id}`}
                        aria-label="Delete document"
                      >
                        <i class="fas fa-trash-alt"></i>
                      </button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          {#if isTableLoading}
            <div class="loading-overlay">
              <span
                class="loading loading-ring text-primary"
                style="width: 80px; height: 80px;"
              ></span>
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
          Displaying {documentsResponse.docs.length === documentsResponse.total
            ? "all"
            : `${(currentPage - 1) * pageSize + 1} - ${Math.min(currentPage * pageSize, documentsResponse.total)}`}
          of {documentsResponse.total} documents
        </div>
        <div class="join">
          <button
            on:click={handleFirstPage}
            disabled={currentPage === 1 || loading || isTableLoading}
            class="join-item btn hover:text-accent/80"
            aria-label="First page"
          >
            «
          </button>
          <button
            on:click={handlePrevPage}
            disabled={currentPage <= 1 || loading || isTableLoading}
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
            disabled={currentPage >= totalPages || loading || isTableLoading}
            class="join-item btn hover:text-accent/80"
            aria-label="Next page"
          >
            ›
          </button>
          <button
            on:click={handleLastPage}
            disabled={currentPage >= totalPages || loading || isTableLoading}
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

<JsonEditor
  bind:isOpen={showEditorSidebar}
  bind:document={documentToEdit}
  on:save={handleSave}
  onClose={() => (showEditorSidebar = false)}
/>

{#if showDeleteModal}
  <Modal
    title="Confirm Deletion"
    message={`Are you sure you want to delete the document with ID "${docToDelete}"? This action cannot be undone.`}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}

<style>
  /* Keyframes for the pulsing animation */
  @keyframes pulse-leaf {
    0%,
    100% {
      transform: scale(1) rotate(0deg);
      filter: brightness(100%);
    }
    50% {
      transform: scale(1.1) rotate(5deg);
      filter: brightness(130%);
    }
  }

  .pulse-leaf {
    font-size: 80px;
    animation: pulse-leaf 2s ease-in-out infinite;
    transform-origin: center bottom;
  }

  /* Custom class to remove padding from the action column cells */
  .no-padding-table-cell {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }

  /* Ensures all table cells are vertically aligned consistently */
  .table-container .table tr td,
  .table-container .table tr th {
    vertical-align: middle;
  }

  /* Styling for the table loading overlay */
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--fallback-b2, oklch(var(--b2) / 0.7));
    z-index: 20;
  }

  /* Query expanded overlay styling */
  .query-expanded-overlay {
    min-width: 400px;
    max-width: 600px;
    width: 100%;
  }

  .query-container {
    position: relative;
  }
</style>
