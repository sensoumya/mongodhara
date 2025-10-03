<script lang="ts">
  import { base } from "$app/paths";
  import { page } from "$app/stores";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import JsonEditor from "$lib/components/JsonEditor.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import SearchAndPagination from "$lib/components/SearchAndPagination.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedDocuments } from "$lib/stores/types";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";

  // SvelteKit store to get URL parameters
  let { db, item } = $page.params;

  // Get the type parameter to determine if this is a collection or GridFS bucket
  $: itemType = $page.url.searchParams.get("type") || "collection";
  $: isCollection = itemType === "collection";
  $: isGridFS = itemType === "gridfs";

  // For backward compatibility, maintain collection variable
  $: collection = item;

  // State for documents and pagination
  let documentsResponse: PaginatedDocuments = {
    docs: [],
    total: 0,
    page: 1,
    page_size: 16, // Consistent page size
  };
  let loading = true;
  let error = false;
  let isTableLoading = false; // New state variable for table loading

  // State for document deletion modal
  let showDeleteModal = false;
  let docToDelete: string | null = null;
  let hoveredRowId: string | null = null; // New state for hover

  // State for file upload modal (GridFS)
  let showUploadModal = false;
  let selectedFile: File | null = null;
  let uploadMetadata: string = "";
  let isUploading = false;

  // State for JSON import modal (Collections)
  let showImportModal = false;
  let selectedImportFile: File | null = null;
  let isImporting = false;

  // State for dropdown actions loading
  let isViewingFile = false;
  let viewingFileId: string | null = null;
  let isDownloading = false;
  let downloadingFileId: string | null = null;
  let isCreatingDocument = false;
  let isImportingFile = false;

  // New state variables for the JSON editor sidebar and query popup
  let showEditorSidebar = false;
  let documentToEdit: any | null = null;
  let isQueryMaximized = false; // New state variable for in-place expansion
  let validationError: string | null = null;

  // State for search/query, pagination, and sorting
  let queryTerm: string = "";
  let currentPage: number = 1;
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
   * Closes dropdowns by removing focus from dropdown elements
   */
  function closeDropdowns() {
    // Find all dropdown triggers and blur them
    const dropdownTriggers = document.querySelectorAll(
      '.dropdown [role="button"]'
    );
    dropdownTriggers.forEach((trigger) => {
      if (trigger instanceof HTMLElement) {
        trigger.blur();
      }
    });
  }

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
   * Fetches data from the server with pagination, sorting, and filtering.
   * Handles both collection documents and GridFS files based on item type.
   * @param isInitialLoad Boolean to indicate if this is the first fetch on mount.
   */
  async function fetchData(isInitialLoad: boolean = false) {
    if (!item) {
      loading = false;
      return;
    }

    if (isInitialLoad) {
      loading = true;
      error = false;
    } else {
      isTableLoading = true;
    }

    try {
      if (isCollection) {
        await fetchDocuments();
      } else if (isGridFS) {
        await fetchGridFSFiles();
      }
    } catch (e) {
      error = true;
      addNotification(
        `Failed to fetch ${isCollection ? "documents" : "files"}.`,
        "error"
      );
    } finally {
      loading = false;
      isTableLoading = false;
    }
  }

  /**
   * Fetches documents from a collection.
   */
  async function fetchDocuments() {
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
        return;
      }
    }

    const body = {
      filter: hasQuery ? parsedQuery : {},
    };

    try {
      const response = await api.apiPost<PaginatedDocuments>(
        `/db/${db}/col/${item}/doc/query?${queryParams.toString()}`,
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
        // Handle case where response structure is unexpected
        documentsResponse = {
          docs: [],
          total: 0,
          page: 1,
          page_size: pageSize,
        };
        addNotification("Unexpected response format from server.", "warning");
      }
    } catch (e) {
      // Handle API errors (network issues, server errors, auth errors, etc.)
      error = true;
      documentsResponse = {
        docs: [],
        total: 0,
        page: 1,
        page_size: pageSize,
      };
      addNotification(e.message, "error");
    }

    allKeys = extractAllKeys(documentsResponse.docs);
  }

  /**
   * Fetches files from a GridFS bucket.
   */
  async function fetchGridFSFiles() {
    // For GridFS, we'll use the existing documents structure but call the GridFS API
    const queryParams = new URLSearchParams();
    queryParams.append("page", currentPage.toString());
    queryParams.append("page_size", pageSize.toString());

    try {
      const response = await api.apiGet(
        `/db/${db}/gridfs/${item}/files?${queryParams.toString()}`
      );
      if (response && response.data) {
        documentsResponse = {
          docs: response.data,
          total: response.total || response.data.length,
          page: response.page || currentPage,
          page_size: response.page_size || pageSize,
        };
        allKeys = extractAllKeys(documentsResponse.docs);
      } else {
        documentsResponse = {
          docs: [],
          total: 0,
          page: 1,
          page_size: pageSize,
        };
      }
    } catch (e) {
      error = true;
      addNotification(e.message, "error");
      documentsResponse = {
        docs: [],
        total: 0,
        page: 1,
        page_size: pageSize,
      };
    }
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
    fetchData();
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
   * Confirms and performs the document/file deletion.
   */
  async function confirmDelete() {
    if (!docToDelete) return;
    try {
      if (isGridFS) {
        await api.apiDelete(`/db/${db}/gridfs/${item}/file/${docToDelete}`);
        addNotification(
          `File with ID "${docToDelete}" deleted successfully.`,
          "success"
        );
      } else {
        await api.apiDelete(`/db/${db}/col/${item}/doc/${docToDelete}`);
        addNotification(
          `Document with ID "${docToDelete}" deleted successfully.`,
          "success"
        );
      }
      await fetchData();
    } catch (e) {
      addNotification(e.message, "error");
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

  /**
   * Handles downloading a GridFS file.
   * @param doc The file document to download.
   */
  async function handleDownloadClick(doc: any) {
    if (!isGridFS) return;

    // Set loading state and close dropdown
    isDownloading = true;
    downloadingFileId = doc._id;
    closeDropdowns();

    try {
      addNotification(`Starting download: ${doc.filename || doc._id}`, "info");

      // Use the API store instead of direct fetch
      const blob = await api.apiDownload(
        `/db/${db}/gridfs/${item}/file/${doc._id}/download`
      );

      // Create a download URL from the blob
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = doc.filename || `file_${doc._id}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up the object URL
      window.URL.revokeObjectURL(downloadUrl);

      addNotification(`File downloaded: ${doc.filename || doc._id}`, "success");
    } catch (e) {
      addNotification(e.message, "error");
    } finally {
      // Clear loading state
      isDownloading = false;
      downloadingFileId = null;
    }
  }

  /**
   * Determines if a file can be viewed in the browser based on extension and size.
   * @param doc The file document.
   * @returns boolean indicating if file is viewable.
   */
  function isFileViewable(doc: any): boolean {
    if (!isGridFS || !doc.filename) return false;

    // Check file size (30MB limit)
    const maxSizeBytes = 30 * 1024 * 1024; // 30MB in bytes
    if (doc.length && doc.length > maxSizeBytes) return false;

    // Check file extension
    const filename = doc.filename.toLowerCase();
    const viewableExtensions = [
      ".json",
      ".txt",
      ".md",
      ".yml",
      ".yaml",
      ".csv",
      ".xml",
      ".log",
      ".conf",
      ".config",
      ".ini",
      ".properties",
    ];

    return viewableExtensions.some((ext) => filename.endsWith(ext));
  }

  /**
   * Gets the file type for display purposes.
   * @param doc The file document.
   * @returns string indicating the file type.
   */
  function getFileType(doc: any): string {
    if (!doc.filename) return "file";

    const filename = doc.filename.toLowerCase();
    if (filename.endsWith(".json")) return "JSON";
    if (filename.endsWith(".txt")) return "Text";
    if (filename.endsWith(".md")) return "Markdown";
    if (filename.endsWith(".yml") || filename.endsWith(".yaml")) return "YAML";
    if (filename.endsWith(".csv")) return "CSV";
    if (filename.endsWith(".xml")) return "XML";
    if (filename.endsWith(".log")) return "Log";
    return "file";
  }

  /**
   * Handles viewing a file in the JSON editor by fetching its content.
   * @param doc The file document to view.
   */
  async function handleViewClick(doc: any) {
    if (!isGridFS || !isFileViewable(doc)) return;

    // Set loading state and close dropdown
    isViewingFile = true;
    viewingFileId = doc._id;
    closeDropdowns();

    try {
      addNotification(
        `Loading ${getFileType(doc)} file: ${doc.filename}`,
        "info"
      );

      // Use the API store instead of direct fetch
      const fileContent = await api.apiDownloadText(
        `/db/${db}/gridfs/${item}/file/${doc._id}/download`
      );

      // Try to parse as JSON for better formatting, otherwise use as plain text
      let documentContent;
      const filename = doc.filename.toLowerCase();

      try {
        if (filename.endsWith(".json")) {
          documentContent = JSON.parse(fileContent);
        } else {
          // For non-JSON files, wrap the content in a structure for display
          documentContent = {
            filename: doc.filename,
            content: fileContent,
            contentType: getFileType(doc),
            fileSize: doc.length,
            uploadDate: doc.uploadDate,
          };
        }
      } catch (e) {
        // If JSON parsing fails, wrap as text content
        documentContent = {
          filename: doc.filename,
          content: fileContent,
          contentType: getFileType(doc),
          fileSize: doc.length,
          uploadDate: doc.uploadDate,
          note: "Content displayed as text (JSON parsing failed)",
        };
      }

      // Open the editor with the file content
      documentToEdit = documentContent;
      showEditorSidebar = true;
    } catch (e) {
      addNotification(e.message, "error");
    } finally {
      // Clear loading state
      isViewingFile = false;
      viewingFileId = null;
    }
  }

  /**
   * Handles page change events from SearchAndPagination component.
   */
  function handlePageChange(event: CustomEvent<{ page: number }>) {
    currentPage = event.detail.page;
    fetchData();
  }

  /**
   * Handles search events from SearchAndPagination component.
   */
  function handleSearch(event: CustomEvent<{ term: string }>) {
    queryTerm = event.detail.term;
    currentPage = 1; // Reset to first page when searching
    fetchData();
  }

  /**
   * Handles form submission for query search.
   */
  function handleQuerySubmit() {
    currentPage = 1;
    fetchData();
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
  async function handleNewDocumentClick() {
    if (!isCollection) {
      addNotification(
        "Document insertion is only supported for collections.",
        "warning"
      );
      return;
    }

    // Set loading state and close dropdown
    isCreatingDocument = true;
    closeDropdowns();

    try {
      documentToEdit = {}; // Initialize with an empty object for a new document
      showEditorSidebar = true;
      addNotification("Opening document editor...", "info");
    } catch (e) {
      addNotification("Failed to open document editor.", "error");
    } finally {
      // Clear loading state
      isCreatingDocument = false;
    }
  }

  /**
   * Handles the click of the "Upload File" button for GridFS.
   */
  function handleUploadClick() {
    if (isGridFS) {
      showUploadModal = true;
    } else {
      handleNewDocumentClick();
    }
  }

  /**
   * Handles file selection for upload.
   */
  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      selectedFile = input.files[0];
    }
  }

  /**
   * Handles file upload to GridFS.
   */
  async function handleFileUpload() {
    if (!selectedFile || !isGridFS) return;

    isUploading = true;
    try {
      // Create FormData for multipart upload
      const formData = new FormData();
      formData.append("file", selectedFile);

      // Add metadata if provided
      if (uploadMetadata.trim()) {
        try {
          // Validate JSON before sending
          JSON.parse(uploadMetadata);
          formData.append("metadata", uploadMetadata);
        } catch (e) {
          addNotification("Invalid JSON in metadata field", "error");
          isUploading = false;
          return;
        }
      } else {
        // Send empty object if no metadata provided
        formData.append("metadata", "{}");
      }

      // Use API utility for upload
      const result = await api.apiUploadFile(
        `/db/${db}/gridfs/${item}/upload`,
        formData
      );
      addNotification(
        `File uploaded successfully: ${selectedFile.name}`,
        "success"
      );

      // Close modal and reset state
      showUploadModal = false;
      selectedFile = null;
      uploadMetadata = "";

      // Refresh the file list
      await fetchData();
    } catch (e) {
      addNotification(e.message, "error");
    } finally {
      isUploading = false;
    }
  }

  /**
   * Cancels the file upload.
   */
  function cancelUpload() {
    showUploadModal = false;
    selectedFile = null;
    uploadMetadata = "";
  }

  /**
   * Handles the click of the "Import JSON file" button.
   */
  async function handleImportClick() {
    if (!isCollection) {
      addNotification(
        "File import is only supported for collections.",
        "warning"
      );
      return;
    }

    // Set loading state and close dropdown
    isImportingFile = true;
    closeDropdowns();

    try {
      showImportModal = true;
      addNotification("Opening file import dialog...", "info");
    } catch (e) {
      addNotification("Failed to open import dialog.", "error");
    } finally {
      // Clear loading state
      isImportingFile = false;
    }
  }

  /**
   * Handles file selection for JSON import.
   */
  function handleImportFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      selectedImportFile = input.files[0];
    }
  }

  /**
   * Handles JSON file import to collection.
   */
  async function handleFileImport() {
    if (!selectedImportFile || !isCollection) return;

    isImporting = true;
    try {
      // Create FormData for multipart upload
      const formData = new FormData();
      formData.append("file", selectedImportFile);

      // Use API utility for import
      const result = await api.apiUploadFile(
        `/db/${db}/col/${item}/import`,
        formData
      );

      addNotification(
        `JSON file imported successfully: ${selectedImportFile.name}`,
        "success"
      );

      // Close modal and reset state
      showImportModal = false;
      selectedImportFile = null;

      // Refresh the document list
      await fetchData();
    } catch (e) {
      addNotification(e.message, "error");
    } finally {
      isImporting = false;
    }
  }

  /**
   * Cancels the JSON file import.
   */
  function cancelImport() {
    showImportModal = false;
    selectedImportFile = null;
  }

  /**
   * Handles the saving of a document from the JsonEditor.
   * This function now handles both creation (POST) and updating (PUT).
   * Note: Only works for collection documents, not GridFS files.
   * @param updatedDoc The document with the updated fields.
   */
  async function handleSave(event: CustomEvent) {
    if (!isCollection) {
      addNotification(
        "Editing is only supported for collection documents.",
        "warning"
      );
      return;
    }

    const updatedDoc = event.detail;
    try {
      if (!updatedDoc._id) {
        delete updatedDoc._id; // Ensure _id is not sent for a new document
        await api.apiPost(`/db/${db}/col/${item}/doc`, {
          data: updatedDoc,
        });
        addNotification("New document created successfully.", "success");
      } else {
        // Use api.apiPut for updating existing documents
        await api.apiPut(`/db/${db}/col/${item}/doc/${updatedDoc._id}`, {
          data: updatedDoc,
        });
        addNotification("Document updated successfully.", "success");
      }

      showEditorSidebar = false;
      await fetchData();
    } catch (e) {
      addNotification(e.message, "error");
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    fetchData(true);
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
    <div>
      <h1 class="text-3xl poppins mb-3 mt-3 text-center">
        {#if isCollection}
          <i class="fas fa-file-alt text-primary"></i>
          Documents
        {:else if isGridFS}
          <i class="fas fa-folder-open text-primary"></i>
          GridFS Files
        {/if}
      </h1>
      <Breadcrumb
        showBackButton={true}
        segments={[
          { name: "Home", isHome: true, href: `${base}/` },
          {
            name: db,
            href: `../${db}?type=${itemType}`,
            label: "Database",
          },
          { name: item, label: isCollection ? "Collection" : "GridFS Bucket" },
        ]}
      />
      <div
        class="flex flex-col md:flex-row justify-between items-center mb-4 space-y-2 md:space-y-0"
      >
        <div class="relative w-full md:w-1/3 query-container">
          <form on:submit|preventDefault={handleQuerySubmit} class="relative">
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
              class="query-expanded-overlay absolute top-0 left-0 w-full bg-base-100 rounded-lg shadow-xl z-50 border-2 border-secondary transition-all duration-300 ease-in-out"
              class:scale-y-0={!isQueryMaximized}
              class:opacity-0={!isQueryMaximized}
              class:scale-y-100={isQueryMaximized}
              class:opacity-100={isQueryMaximized}
              style="transform-origin: top left;"
              on:click|stopPropagation
            >
              <div class="relative p-4">
                <!-- Moved buttons to top-right -->
                <div
                  class="absolute top-4 right-4 flex items-center gap-2 z-10"
                >
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

                <textarea
                  bind:value={queryTerm}
                  class="textarea w-full h-96 font-mono text-sm resize-none border-none focus:outline-none bg-transparent pr-40"
                  placeholder="Enter JSON query..."
                ></textarea>
                {#if validationError}
                  <div class="text-sm text-error mt-2">
                    Error: {validationError}
                  </div>
                {/if}
              </div>
            </div>
          </form>

          <!-- Backdrop for click-outside-to-close -->
          <div
            class="fixed inset-0 z-40 bg-transparent transition-opacity duration-300 ease-in-out"
            class:opacity-0={!isQueryMaximized}
            class:opacity-100={isQueryMaximized}
            class:pointer-events-none={!isQueryMaximized}
            on:click={() => (isQueryMaximized = false)}
          ></div>
        </div>
        {#if isGridFS}
          <button
            on:click={handleUploadClick}
            class="btn btn-secondary px-4 py-3 rounded-md transition-colors duration-300 tooltip"
            data-tip="Upload file"
            aria-label="Upload file"
          >
            <i class="fas fa-arrow-up-from-bracket mr-0"></i>
          </button>
        {:else}
          <!-- Collections dropdown -->
          <div
            class="dropdown dropdown-end dropdown-hover"
            class:hidden={showEditorSidebar}
          >
            <div
              tabindex="0"
              role="button"
              class="btn btn-secondary px-4 py-3 rounded-md transition-colors duration-300 tooltip"
              data-tip="Add to collection"
            >
              <i class="fas fa-plus mr-0"></i>
            </div>
            <ul
              tabindex="0"
              class="dropdown-content menu bg-base-100 rounded-box z-[1] w-60 p-2 shadow-xl border border-base-300"
            >
              <li>
                <button
                  on:click={handleNewDocumentClick}
                  class="flex items-center gap-3 py-3 px-3 hover:bg-base-200 hover:text-primary rounded-lg transition-colors"
                  disabled={isCreatingDocument}
                >
                  {#if isCreatingDocument}
                    <span class="loading loading-spinner loading-xs"></span>
                    Opening Editor...
                  {:else}
                    <i class="fa-solid fa-file-circle-plus"></i>
                    <span>Insert a document</span>
                  {/if}
                </button>
              </li>
              <li>
                <button
                  on:click={handleImportClick}
                  class="flex items-center gap-3 py-3 px-3 hover:bg-base-200 hover:text-primary rounded-lg transition-colors"
                  disabled={isImportingFile}
                >
                  {#if isImportingFile}
                    <span class="loading loading-spinner loading-xs"></span>
                    Opening Import...
                  {:else}
                    <i class="fa-solid fa-arrow-up-from-bracket"></i>
                    <span>Import a JSON file</span>
                  {/if}
                </button>
              </li>
            </ul>
          </div>
        {/if}
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
        </div>
      {:else if error}
        <div
          class="text-center text-secondary/40 h-full flex flex-col justify-center"
        >
          <p class="text-2xl font-semibold poppins">Unable to load content</p>
        </div>
      {:else if documentsResponse.docs.length === 0}
        <div
          class="text-center text-secondary/40 h-full flex flex-col justify-center"
        >
          <p class="text-2xl font-semibold poppins">No content available</p>
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
                      ? 'bg-neutral/20'
                      : 'hover:bg-neutral/20'}"
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
            <table class="table" style="width: 60px;">
              <thead>
                <tr class="bg-primary/40 poppins">
                  <th class="text-center w-full">&nbsp;</th>
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
                      ? 'bg-neutral/20'
                      : 'hover:bg-neutral/20'}"
                  >
                    <td class="text-center no-padding-table-cell">
                      <div
                        class="dropdown dropdown-end dropdown-hover"
                        class:hidden={showEditorSidebar}
                      >
                        <div
                          tabindex="0"
                          role="button"
                          class="btn btn-ghost btn-sm hover:bg-base-200"
                          on:click|stopPropagation
                        >
                          <i class="fa-solid fa-ellipsis-vertical"></i>
                        </div>
                        <ul
                          tabindex="0"
                          class="dropdown-content z-[1] menu p-2 shadow-lg bg-base-100 rounded-box w-48 border border-base-300"
                          on:click|stopPropagation
                        >
                          {#if isGridFS && isFileViewable(doc)}
                            <li>
                              <button
                                on:click={() => handleViewClick(doc)}
                                class="flex items-center gap-2 text-sm hover:bg-base-200 hover:text-primary"
                                disabled={isViewingFile &&
                                  viewingFileId === doc._id}
                              >
                                {#if isViewingFile && viewingFileId === doc._id}
                                  <span
                                    class="loading loading-spinner loading-xs"
                                  ></span>
                                  Loading...
                                {:else}
                                  <i class="fa-solid fa-eye"></i>
                                  View in Browser
                                {/if}
                              </button>
                            </li>
                          {/if}
                          {#if isGridFS}
                            <li>
                              <button
                                on:click={() => handleDownloadClick(doc)}
                                class="flex items-center gap-2 text-sm hover:bg-base-200 hover:text-primary"
                                disabled={isDownloading &&
                                  downloadingFileId === doc._id}
                              >
                                {#if isDownloading && downloadingFileId === doc._id}
                                  <span
                                    class="loading loading-spinner loading-xs"
                                  ></span>
                                  Downloading...
                                {:else}
                                  <i class="fa-solid fa-cloud-arrow-down"></i>
                                  Download File
                                {/if}
                              </button>
                            </li>
                          {/if}
                          <li>
                            <button
                              on:click={() => handleDeleteClick(doc)}
                              class="flex items-center gap-2 text-sm hover:bg-base-200 hover:text-error"
                            >
                              <i class="fas fa-trash-alt"></i>
                              Delete {isGridFS ? "File" : "Document"}
                            </button>
                          </li>
                        </ul>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          {#if isTableLoading}
            <div class="loading-overlay loading-overlay-table">
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
        <div class="text-sm text-accent">
          Displaying {documentsResponse.docs.length === documentsResponse.total
            ? "all"
            : `${(currentPage - 1) * pageSize + 1} - ${Math.min(currentPage * pageSize, documentsResponse.total)}`}
          of {documentsResponse.total}
          {isGridFS ? "files" : "documents"}
        </div>

        <SearchAndPagination
          {currentPage}
          {totalPages}
          loading={loading || isTableLoading}
          showSearch={false}
          showCreateButton={false}
          on:pageChange={handlePageChange}
        />
      </div>
    </div>
  </div>
</div>

<JsonEditor
  bind:isOpen={showEditorSidebar}
  bind:document={documentToEdit}
  readOnly={isGridFS}
  on:save={handleSave}
  onClose={() => (showEditorSidebar = false)}
/>

{#if showDeleteModal}
  <Modal
    title="Confirm Deletion"
    message={`Are you sure you want to delete the ${isGridFS ? "file" : "document"} with ID "${docToDelete}"? This action cannot be undone.`}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}

{#if showUploadModal}
  <Modal
    title="Upload File to GridFS"
    message=""
    onConfirm={handleFileUpload}
    onCancel={cancelUpload}
    confirmButtonText={isUploading ? "Uploading..." : "Upload"}
    confirmDisabled={!selectedFile || isUploading}
    validationMessage={!selectedFile ? "Please select a file to upload" : ""}
  >
    <div class="form-control w-full mb-4">
      <label class="label">
        <span class="label-text">Select File</span>
      </label>
      <input
        type="file"
        class="file-input file-input-bordered file-input-secondary w-full"
        on:change={handleFileSelect}
        disabled={isUploading}
      />
    </div>

    <div class="form-control w-full mb-6">
      <label class="label">
        <span class="label-text">Metadata (JSON)</span>
      </label>
      <textarea
        class="textarea textarea-bordered w-full h-24 input-secondary"
        bind:value={uploadMetadata}
        placeholder={'{"key": "value"}'}
        disabled={isUploading}
      ></textarea>
    </div>
  </Modal>
{/if}

{#if showImportModal}
  <Modal
    title="Import JSON File to Collection"
    message=""
    onConfirm={handleFileImport}
    onCancel={cancelImport}
    confirmButtonText={isImporting ? "Importing..." : "Import"}
    confirmDisabled={!selectedImportFile || isImporting}
    validationMessage={!selectedImportFile
      ? "Please select a JSON file to import"
      : ""}
  >
    <div class="form-control w-full mb-4">
      <label class="label">
        <span class="label-text">Select JSON File</span>
      </label>
      <input
        type="file"
        accept=".json"
        class="file-input file-input-bordered file-input-secondary w-full"
        on:change={handleImportFileSelect}
        disabled={isImporting}
      />
    </div>

    <div class="form-control w-full mb-6">
      <label class="label">
        <span class="label-text">Description</span>
      </label>
      <p class="text-sm text-base-content/70">
        This will import documents from the JSON file into the collection. The
        file should contain either a single JSON object or an array of JSON
        objects.
      </p>
    </div>

    {#if isImporting}
      <div class="flex items-center gap-2 text-sm text-base-content/70 mb-4">
        <span class="loading loading-spinner loading-sm"></span>
        <span>Importing file...</span>
      </div>
    {/if}
  </Modal>
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
    transition: background-color 0.3s;
  }

  /* Add this for table loading overlay */
  .loading-overlay-table {
    background-color: transparent !important;
    pointer-events: none;
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

  /* Action dropdown styling */
  .dropdown-hover:hover .dropdown-content {
    visibility: visible;
    opacity: 1;
  }

  .dropdown-content {
    visibility: hidden;
    opacity: 0;
    transition:
      opacity 0.2s ease,
      visibility 0.2s ease;
  }

  .dropdown-content li button {
    width: 100%;
    justify-content: flex-start;
    border-radius: 0.375rem;
    padding: 0.5rem;
    transition: background-color 0.15s ease;
  }

  .dropdown-content li button:hover {
    background-color: var(--fallback-b2, oklch(var(--b2)));
  }

  /* Ensure dropdown appears above other elements */
  .dropdown-content {
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  }

  /* Custom tooltip styles for long text */
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
