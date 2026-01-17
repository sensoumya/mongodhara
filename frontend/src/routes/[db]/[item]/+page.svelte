<script lang="ts">
  import { base } from "$app/paths";
  import { page } from "$app/stores";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import JsonEditor from "$lib/components/JsonEditor.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import MongoQueryInput from "$lib/components/MongoQueryInput.svelte";
  import Pagination from "$lib/components/Pagination.svelte";
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

  // Display names for breadcrumb (populated from API responses)
  let dbDisplayName = "";
  let itemDisplayName = "";

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
  let jsonEditor: JsonEditor; // Reference to JsonEditor component

  // New state variables for the JSON editor sidebar
  let showEditorSidebar = false;
  let documentToEdit: any | null = null;

  // State for search/query, pagination, and sorting
  let queryTerm: string = "";
  let currentPage: number = 1;
  let pageSize: number =
    typeof window !== "undefined"
      ? parseInt(localStorage.getItem("pageSize_documents") || "14")
      : 14;
  // Total number of pages for the pagination dropdown
  $: totalPages = Math.ceil(documentsResponse.total / pageSize);

  // Save pageSize to localStorage whenever it changes
  $: if (typeof window !== "undefined") {
    localStorage.setItem("pageSize_documents", pageSize.toString());
  }

  // New state variables for sorting, initialized to null so they are not sent by default
  let sortField: string | null = null;
  let sortOrder: 1 | -1 | null = null;

  // List of all unique keys from all documents for the table headers
  let allKeys: string[] = [];
  const maxLength = 50;

  // Pinned columns (moved to front). Persisted in localStorage per db+collection
  const MAX_PINNED = 3; // maximum number of pinned columns allowed
  let pinnedColumns: string[] = [];

  // Computed: check if pin limit is reached
  $: isPinLimitReached = pinnedColumns.length >= MAX_PINNED;

  // References to the table bodies for height synchronization
  let mainTableBody: HTMLTableSectionElement;
  let actionTableBody: HTMLTableSectionElement;

  // Load pinned columns from localStorage on mount (scoped by db+collection)
  function loadPinnedColumns() {
    try {
      if (typeof window === "undefined") return;
      const key = `pinnedColumns:${db}:${item}`;
      const stored = localStorage.getItem(key);
      if (!stored) return;

      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) pinnedColumns = parsed;
        else if (typeof parsed === "string") pinnedColumns = [parsed];
      } catch (e) {
        // Backwards compatibility: if stored is a plain string (old behavior)
        pinnedColumns = [stored];
      }
    } catch (e) {
      // ignore storage errors
    }
  }

  function savePinnedColumns() {
    try {
      if (typeof window === "undefined") return;
      const key = `pinnedColumns:${db}:${item}`;
      if (pinnedColumns && pinnedColumns.length > 0)
        localStorage.setItem(key, JSON.stringify(pinnedColumns));
      else localStorage.removeItem(key);
    } catch (e) {
      // ignore storage errors
    }
  }

  function togglePinnedColumn(key: string) {
    const idx = pinnedColumns.indexOf(key);
    if (idx >= 0) {
      // unpin
      pinnedColumns.splice(idx, 1);
      pinnedColumns = pinnedColumns; // trigger reactivity
    } else {
      // pin (respect limit)
      if (pinnedColumns.length >= MAX_PINNED) {
        addNotification(
          `Maximum ${MAX_PINNED} pinned columns allowed. Unpin another to add this one.`,
          "warning"
        );
        return;
      }
      pinnedColumns = [...pinnedColumns, key]; // trigger reactivity
    }
    savePinnedColumns();
    // Recompute keys ordering
    allKeys = extractAllKeys(documentsResponse.docs, pinnedColumns);
  }

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
   * Checks if a document should be protected from deletion
   */
  function isProtectedDocument(
    dbName: string,
    collectionName: string
  ): boolean {
    const systemDatabases = ["admin", "local", "config", "mongodhara"];
    const systemCollections = [
      "system.users",
      "system.roles",
      "system.version",
      "system.namespaces",
    ];

    // Protect all documents in system databases
    if (systemDatabases.includes(dbName)) {
      return true;
    }

    // Protect documents in system collections
    return systemCollections.includes(collectionName);
  }

  /**
   * Extracts and sorts all unique keys from a list of documents based on a specific order.
   * - When columns are pinned: pinned columns first, then _id, then rest
   * - When no columns are pinned: _id first, then rest
   * - Rest: columns with 'id' in their name (case-insensitive), sorted alphabetically.
   * - Then, columns with 'name' in their name (case-insensitive), sorted alphabetically.
   * - Finally, all other columns, sorted alphabetically.
   * @param docs An array of document objects.
   * @param pinnedKeys Array of pinned column keys to place at front.
   * @returns An array of unique, sorted keys.
   */
  function extractAllKeys(docs: any[], pinnedKeys: string[] = []): string[] {
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
    let hasId = false;

    allUniqueKeys.forEach((key) => {
      if (key === "_id") {
        hasId = true;
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

    // Construct sorted array based on pinned columns
    let sorted: string[] = [];

    if (pinnedKeys && pinnedKeys.length > 0) {
      // When columns are pinned: pinned columns first (with _id at the beginning if pinned), then rest
      const validPinned = pinnedKeys.filter(pk => pk && allUniqueKeys.has(pk));
      const remaining = [hasId && !validPinned.includes("_id") ? "_id" : null, ...idKeys, ...nameKeys, ...otherKeys].filter(Boolean) as string[];
      // Remove pinned keys from remaining
      const remainingFiltered = remaining.filter(k => !validPinned.includes(k));
      sorted = [...validPinned, ...remainingFiltered];
    } else {
      // When no columns are pinned: _id first (if exists), then rest
      sorted = hasId ? ["_id", ...idKeys, ...nameKeys, ...otherKeys] : [...idKeys, ...nameKeys, ...otherKeys];
    }

    return sorted;
  }

  // Debounce timeout for height synchronization
  let syncTimeout: number;

  /**
   * Synchronizes the heights of action table rows with main table rows
   * Uses a more robust approach that handles dynamic content and zoom changes
   */
  function synchronizeRowHeights() {
    if (
      !mainTableBody ||
      !actionTableBody ||
      documentsResponse.docs.length === 0
    ) {
      return;
    }

    // Clear any pending synchronization
    if (syncTimeout) {
      clearTimeout(syncTimeout);
    }

    // Debounce the synchronization to avoid excessive calls
    syncTimeout = setTimeout(() => {
      requestAnimationFrame(() => {
        const mainRows = mainTableBody.querySelectorAll("tr");
        const actionRows = actionTableBody.querySelectorAll("tr");

        // Check if the number of rows matches to prevent errors
        if (mainRows.length !== actionRows.length) {
          // Try again after a short delay if DOM is still updating
          setTimeout(() => synchronizeRowHeights(), 50);
          return;
        }

        mainRows.forEach((mainRow, index) => {
          const actionRow = actionRows[index];
          if (actionRow) {
            // Use getBoundingClientRect for more accurate height calculation
            const mainHeight = mainRow.getBoundingClientRect().height;
            actionRow.style.height = `${mainHeight}px`;
            // Also set min-height to prevent content overflow issues
            actionRow.style.minHeight = `${mainHeight}px`;
          }
        });
      });
    }, 16); // ~60fps debounce
  }

  // Reactive block to trigger height synchronization when data changes
  $: if (
    mainTableBody &&
    actionTableBody &&
    documentsResponse.docs.length > 0
  ) {
    synchronizeRowHeights();
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
      // Synchronize row heights after loading is complete
      synchronizeRowHeights();
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
        // Extract display names from API response
        if (response.database?.name) {
          dbDisplayName = response.database.name;
        }
        if (response.collection?.name) {
          itemDisplayName = response.collection.name;
        }

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

    allKeys = extractAllKeys(documentsResponse.docs, pinnedColumns);
  }

  /**
   * Fetches files from a GridFS bucket.
   */
  async function fetchGridFSFiles() {
    // Mirror documents query: POST with JSON filter + pagination/sorting
    const queryParams = new URLSearchParams();
    queryParams.append("page", currentPage.toString());
    queryParams.append("page_size", pageSize.toString());
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
        // For GridFS, allow simple string search fallback on filename
        parsedQuery = { filename: { $regex: queryTerm.trim(), $options: "i" } };
        hasQuery = true;
      }
    }

    const body = {
      filter: hasQuery ? parsedQuery : {},
    };

    try {
      const response = await api.apiPost(
        `/db/${db}/gridfs/${item}/files/query?${queryParams.toString()}`,
        body
      );
      if (response && response.data) {
        // Extract display names from API response
        if (response.database?.name) {
          dbDisplayName = response.database.name;
        }
        if (response.bucket?.bucket_name) {
          itemDisplayName = response.bucket.bucket_name;
        }

        documentsResponse = {
          docs: response.data,
          total: response.total ?? response.data.length ?? 0,
          page: response.page ?? currentPage,
          page_size: response.page_size ?? pageSize,
        };
        allKeys = extractAllKeys(documentsResponse.docs, pinnedColumns);
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
      // Close modal immediately after successful delete
      showDeleteModal = false;
      docToDelete = null;
      // Refresh data after modal is closed
      await fetchData();
    } catch (e) {
      addNotification(e.message, "error");
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

    // Check file size (5MB limit)
    const maxSizeBytes = 5 * 1024 * 1024; // 5MB in bytes
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
   * Handles page change events from Pagination component.
   */
  function handlePageChange(event: CustomEvent<{ page: number }>) {
    currentPage = event.detail.page;
    fetchData();
  }

  /**
   * Handles search events.
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
   * Handles refetching data and updating the editor with fresh document.
   */
  async function handleRefetch() {
    if (!documentToEdit || !documentToEdit._id) {
      handleQuerySubmit();
      jsonEditor?.refetchComplete();
      return;
    }

    const currentDocId = documentToEdit._id;

    // Use isTableLoading instead of fetchData to avoid central spinner
    isTableLoading = true;
    try {
      if (isCollection) {
        await fetchDocuments();
      } else if (isGridFS) {
        await fetchGridFSFiles();
      }
    } catch (e) {
      // Error handling is already done in fetchDocuments/fetchGridFSFiles
    } finally {
      isTableLoading = false;
    }

    // Find the updated document in the refreshed data and update the editor
    const updatedDoc = documentsResponse.docs.find(
      (doc: any) => doc._id === currentDocId
    );
    if (updatedDoc) {
      documentToEdit = updatedDoc;
    }

    // Notify the editor that refetch is complete
    jsonEditor?.refetchComplete();
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
      formData.append("bucket_name", itemDisplayName);

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
        `/db/${db}/gridfs/upload`,
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
      jsonEditor?.saveComplete();
    } catch (e) {
      addNotification(e.message, "error");
      jsonEditor?.saveFailed();
    }
  }

  // Initial data fetch on component mount
  onMount(() => {
    loadPinnedColumns();
    fetchData(true);

    // Add resize event listener for height synchronization on zoom/resize
    const handleResize = () => {
      synchronizeRowHeights();
    };

    window.addEventListener("resize", handleResize);

    // Return cleanup function for onDestroy
    return () => {
      window.removeEventListener("resize", handleResize);
      if (syncTimeout) {
        clearTimeout(syncTimeout);
      }
    };
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
        {#if isCollection}
          <span class="flex items-center gap-2">
            <i class="fas fa-file-alt text-primary"></i>
            <span>Documents</span>
          </span>
        {:else if isGridFS}
          <span class="flex items-center gap-2">
            <i class="fas fa-folder-open text-primary"></i>
            <span>GridFS Files</span>
          </span>
        {/if}
      </h1>

      <!-- Breadcrumb and Controls Row -->
      <div
        class="flex flex-col md:flex-row md:items-center justify-between mb-2 gap-2"
      >
        <div class="flex-1">
          <Breadcrumb
            showBackButton={true}
            segments={[
              { name: "Home", isHome: true, href: `${base}/` },
              {
                name: dbDisplayName,
                href: `../${db}?type=${itemType}`,
                label: "Database",
                loading: loading && !dbDisplayName,
              },
              {
                name: itemDisplayName,
                label: isCollection ? "Collection" : "GridFS Bucket",
                loading: loading && !itemDisplayName,
              },
            ]}
          />
        </div>
        <div class="flex items-center gap-2">
          <MongoQueryInput
            bind:value={queryTerm}
            availableFields={allKeys}
            disabled={loading || isTableLoading}
            on:submit={handleQuerySubmit}
          />

          {#if isGridFS}
            {#if !isProtectedDocument(dbDisplayName, itemDisplayName)}
              <div
                class="flex items-center gap-0.5"
                class:opacity-0={showEditorSidebar}
                class:pointer-events-none={showEditorSidebar}
              >
                <button
                  on:click={handleUploadClick}
                  class="btn btn-secondary btn-sm flex items-center px-2"
                  aria-label="Upload file"
                >
                  <i class="fas fa-arrow-up-from-bracket"></i>
                  <span class="hidden md:inline">Upload</span>
                </button>
              </div>
            {/if}
          {:else}
            <!-- Collections dropdown -->
            {#if !isProtectedDocument(dbDisplayName, itemDisplayName)}
              <div
                class="dropdown dropdown-end dropdown-hover"
                class:opacity-0={showEditorSidebar}
                class:pointer-events-none={showEditorSidebar}
              >
                <div
                  tabindex="0"
                  role="button"
                  class="btn btn-secondary btn-sm flex items-center gap-1"
                >
                  <i class="fas fa-plus"></i>
                  <span class="hidden md:inline">Add</span>
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
                        <span class="loading loading-ring loading-xs"></span>
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
                        <span class="loading loading-ring loading-xs"></span>
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
          {/if}
        </div>
      </div>
    </div>

    <!-- Separator line -->
    <div class="border-t border-base-content/10 mb-3"></div>

    <!-- Main Content Area -->
    <div
      class="flex-grow overflow-y-auto mb-4 table-container rounded-box relative shadow-2xl"
    >
      {#if loading && !showEditorSidebar}
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
      {/if}

      {#if isTableLoading && !showEditorSidebar}
        <div class="loading-overlay loading-overlay-table">
          <span
            class="loading loading-ring text-primary"
            style="width: 80px; height: 80px;"
          ></span>
        </div>
      {/if}

      {#if error}
        <div
          class="text-center text-secondary/40 h-full flex flex-col justify-center"
        >
          <p class="text-2xl font-semibold poppins">Unable to load content</p>
        </div>
      {:else if documentsResponse.docs.length === 0}
        <div
          class="text-center text-secondary/60 h-full flex flex-col justify-center"
        >
          <p class="text-2xl font-semibold poppins">No content available</p>
        </div>
      {:else}
        <div class="flex relative rounded-box">
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
                        <span class="flex-1">{key}</span>
                        <div class="flex items-center gap-1">
                          {#if sortField === key}
                            {#if sortOrder === 1}
                              <i class="fas fa-arrow-up text-xs"></i>
                            {:else}
                              <i class="fas fa-arrow-down text-xs"></i>
                            {/if}
                          {/if}

                          <!-- Pin button with compact styling -->
                          <button
                            on:click|stopPropagation={() => togglePinnedColumn(key)}
                            class="pin-btn"
                            class:pinned={pinnedColumns.includes(key)}
                            class:cursor-not-allowed={!pinnedColumns.includes(key) && isPinLimitReached}
                            disabled={!pinnedColumns.includes(key) && isPinLimitReached}
                            aria-pressed={pinnedColumns.includes(key)}
                            aria-label={pinnedColumns.includes(key) ? `Unpin column ${key}` : isPinLimitReached ? `Cannot pin - limit reached` : `Pin column ${key}`}
                          >
                            {#if pinnedColumns.includes(key)}
                              <i class="fa-solid fa-square-check"></i>
                            {:else}
                              <i class="fa-regular fa-square"></i>
                            {/if}
                          </button>
                        </div>
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
                  <th class="text-center w-full">
                    <div class="flex items-center justify-center" style="min-height: 20px;">
                      <span style="opacity: 0;">.</span>
                    </div>
                  </th>
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
                        class:opacity-0={showEditorSidebar}
                        class:pointer-events-none={showEditorSidebar}
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
                                  <span class="loading loading-ring loading-xs"
                                  ></span>
                                  Loading...
                                {:else}
                                  <i class="fa-solid fa-eye"></i>
                                  View File Content
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
                                  <span class="loading loading-ring loading-xs"
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
                              class="flex items-center gap-2 text-sm {isProtectedDocument(
                                dbDisplayName,
                                itemDisplayName
                              )
                                ? 'text-base-content/30 cursor-not-allowed opacity-50'
                                : 'hover:bg-base-200 hover:text-error'}"
                              disabled={isProtectedDocument(
                                dbDisplayName,
                                itemDisplayName
                              )}
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
        </div>
      {/if}
    </div>

    <!-- Pagination Controls -->
    <Pagination
      {currentPage}
      {totalPages}
      {pageSize}
      loading={loading || isTableLoading}
      showPageSize={true}
      on:pageChange={handlePageChange}
      on:pageSizeChange={(e) => {
        pageSize = e.detail.pageSize;
        currentPage = 1;
        fetchData();
      }}
    />
  </div>
</div>

<JsonEditor
  bind:this={jsonEditor}
  bind:isOpen={showEditorSidebar}
  bind:document={documentToEdit}
  readOnly={isGridFS}
  showRefetch={documentToEdit && documentToEdit._id ? true : false}
  on:save={handleSave}
  on:refetch={handleRefetch}
  onClose={() => (showEditorSidebar = false)}
/>

<Modal
  title="Confirm Deletion"
  message={`Are you sure you want to delete the ${isGridFS ? "file" : "document"} with ID "${docToDelete}"? This action cannot be undone.`}
  onConfirm={confirmDelete}
  onCancel={cancelDelete}
  show={showDeleteModal}
/>

<Modal
  title="Upload File to GridFS"
  message=""
  onConfirm={handleFileUpload}
  onCancel={cancelUpload}
  confirmButtonText={isUploading ? "Uploading..." : "Upload"}
  confirmDisabled={!selectedFile || isUploading}
  validationMessage={!selectedFile ? "Please select a file to upload" : ""}
  show={showUploadModal}
>
  <div class="form-control w-full mb-4">
    <label class="label">
      <span class="label-text">Select File</span>
    </label>
    <input
      type="file"
      class="file-input file-input-bordered w-full"
      on:change={handleFileSelect}
      disabled={isUploading}
    />
  </div>

  <div class="form-control w-full mb-6">
    <label class="label">
      <span class="label-text">Metadata (JSON)</span>
    </label>
    <textarea
      class="textarea textarea-bordered w-full h-24"
      bind:value={uploadMetadata}
      placeholder={'{"key": "value"}'}
      disabled={isUploading}
    ></textarea>
  </div>
</Modal>

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
  show={showImportModal}
>
  <div class="form-control w-full mb-4">
    <label class="label">
      <span class="label-text">Select JSON File</span>
    </label>
    <input
      type="file"
      accept=".json"
      class="file-input file-input-bordered w-full"
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
</Modal>

<style>
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
    z-index: 70;
    transition: background-color 0.3s;
  }

  /* Add this for table loading overlay */
  .loading-overlay-table {
    background-color: rgba(var(--b1), 0.8) !important;
    pointer-events: none;
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

  .pin-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    padding: 0;
    border: 1px solid var(--fallback-bc, oklch(var(--bc) / 0.2));
    border-radius: 50%;
    background: transparent;
    cursor: pointer;
    transition: all 0.15s ease;
    flex-shrink: 0;
  }

  .pin-btn i {
    font-size: 10px;
    opacity: 0.5;
    transition: opacity 0.15s ease;
  }

  .pin-btn:hover {
    background: var(--fallback-b2, oklch(var(--b2)));
    border-color: var(--fallback-bc, oklch(var(--bc) / 0.4));
  }

  .pin-btn:hover i {
    opacity: 0.8;
  }

  .pin-btn.pinned {
    background: var(--fallback-p, oklch(var(--p) / 0.1));
    border-color: var(--fallback-p, oklch(var(--p) / 0.4));
  }

  .pin-btn.pinned i {
    color: var(--fallback-p, oklch(var(--p)));
    opacity: 1;
  }

  .pin-btn.pinned:hover {
    background: var(--fallback-p, oklch(var(--p) / 0.2));
    border-color: var(--fallback-p, oklch(var(--p) / 0.6));
  }

  /* Disabled pin button styling - show not-allowed cursor */
  .pin-btn:disabled,
  .pin-btn.cursor-not-allowed {
    cursor: not-allowed !important;
  }

  .pin-btn:disabled:hover {
    background: transparent;
    border-color: var(--fallback-bc, oklch(var(--bc) / 0.2));
  }

  .pin-btn:disabled:hover i {
    opacity: 0.5;
  }
</style>
