<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import Modal from "$lib/components/Modal.svelte";
  import StatsPopover from "$lib/components/StatsPopover.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { GridFSBucket, PaginatedGridFSBuckets } from "$lib/stores/types";
  import { onDestroy, onMount } from "svelte";
  import { fade } from "svelte/transition";

  export let db: string;
  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let loading: boolean = false;
  export let pageSize: number = 16;
  export let isLoading: boolean = false;
  let error: boolean = false;

  export let gridfsResponse: PaginatedGridFSBuckets = {
    database: {
      name: "",
      opaque_id: "",
    },
    buckets: [],
    total: 0,
    page: 1,
    page_size: 16,
  };

  let showDeleteBucketModal = false;
  let bucketToDelete: string | null = null;
  let bucketToDeleteName: string | null = null;
  let showCreateBucketModal = false;
  let newBucketName: string = "";
  let selectedFile: File | null = null;
  let bucketMetadataString: string = "";
  let bucketMetadata: Record<string, any> = {};

  // Stats popover state
  let showStatsPopover: string | null = null;
  let statsData: any = null;
  let statsLoading: boolean = false;
  let statsCache: { [key: string]: any } = {};
  let loadingStats: { [key: string]: boolean } = {};

  // Copy functionality
  let justCopied: string | null = null;

  export let totalPages = Math.ceil(gridfsResponse.total / pageSize);
  $: totalPages = Math.ceil(gridfsResponse.total / pageSize);

  // Track which bucket names are overflowing
  let overflowingBuckets = new Set<string>();

  // Svelte action to check text overflow
  function checkTextOverflow(element: HTMLElement, bucketName: string) {
    function updateOverflow() {
      // Small delay to ensure CSS is applied
      setTimeout(() => {
        const isOverflowing = element.scrollWidth > element.clientWidth;

        if (isOverflowing) {
          overflowingBuckets.add(bucketName);
        } else {
          overflowingBuckets.delete(bucketName);
        }
        overflowingBuckets = new Set(overflowingBuckets); // Trigger reactivity
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

  /**
   * Checks if a GridFS bucket should be protected from deletion
   */
  function isProtectedBucket(dbName: string): boolean {
    const systemDatabases = ["admin", "local", "config", "mongodhara"];
    // Protect all buckets in system databases
    return systemDatabases.includes(dbName);
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
   * Navigates to the GridFS bucket detail page.
   * @param bucket The bucket object to navigate to.
   */
  function handleBucketClick(bucket: GridFSBucket) {
    goto(
      `${base}/${gridfsResponse.database.opaque_id}/${bucket.opaque_id}?type=gridfs`
    );
  }

  /**
   * Fetches the list of GridFS buckets for the current database.
   */
  export async function fetchGridFSBuckets(forceRefresh: boolean = false) {
    // Skip if data is already loaded and not forcing refresh (for tab switching optimization)
    if (!forceRefresh && gridfsResponse.buckets.length > 0) {
      return;
    }

    isLoading = true;
    error = false;
    try {
      const query = new URLSearchParams();

      if (searchTerm.trim() !== "") {
        query.append("search", searchTerm);
      }

      query.append("page", currentPage.toString());
      query.append("page_size", pageSize.toString());

      const response = await api.apiGet<PaginatedGridFSBuckets>(
        `/db/${db}/gridfs?${query.toString()}`
      );
      gridfsResponse = response;
    } catch (e) {
      error = true;
      addNotification(e instanceof Error ? e.message : String(e), "error");
      gridfsResponse = {
        database: {
          name: "",
          opaque_id: "",
        },
        buckets: [],
        total: 0,
        page: 1,
        page_size: 16,
      };
    } finally {
      isLoading = false;
    }
  }

  /**
   * Sets up the bucket deletion confirmation modal.
   */
  function handleDeleteBucketClick(bucketName: string) {
    showDeleteBucketModal = true;
    bucketToDelete = bucketName;
  }

  /**
   * Shows the create bucket modal.
   */
  export function openCreateBucketModal() {
    showCreateBucketModal = true;
  }

  /**
   * Confirms and performs the bucket deletion.
   */
  async function confirmDeleteBucket() {
    if (!bucketToDelete) return;

    try {
      await api.apiDelete(`/db/${db}/gridfs/${bucketToDelete}`);

      // Close modal and show page loader immediately after API call completes
      const bucketNameForNotification = bucketToDeleteName;
      showDeleteBucketModal = false;
      bucketToDelete = null;
      bucketToDeleteName = null;

      // Show page loader while fetching updated data
      isLoading = true;

      addNotification(
        `Bucket "${bucketNameForNotification}" deleted successfully.`,
        "success"
      );
      gridfsResponse.buckets = []; // Clear cache to force refetch
      await fetchGridFSBuckets();
    } catch (e) {
      showDeleteBucketModal = false;
      bucketToDelete = null;
      bucketToDeleteName = null;
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Cancels the bucket deletion.
   */
  function cancelDeleteBucket() {
    showDeleteBucketModal = false;
    bucketToDelete = null;
    bucketToDeleteName = null;
  }

  /**
   * Handles file selection for bucket creation.
   */
  function handleFileSelect(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files[0]) {
      selectedFile = target.files[0];
    }
  }

  /**
   * Handles the creation of a new GridFS bucket with file upload.
   */
  async function handleCreateBucket() {
    try {
      const formData = new FormData();
      formData.append("file", selectedFile!);
      formData.append("bucket_name", newBucketName);

      // Parse and add metadata if provided
      if (bucketMetadataString.trim()) {
        try {
          bucketMetadata = JSON.parse(bucketMetadataString);
          formData.append("metadata", JSON.stringify(bucketMetadata));
        } catch (parseError) {
          addNotification("Invalid JSON in metadata field.", "error");
          return;
        }
      }

      await api.apiUploadFile(
        `/db/${gridfsResponse.database.opaque_id}/gridfs/upload`,
        formData
      );
      addNotification(
        `Bucket "${newBucketName}" created successfully with file "${selectedFile!.name}".`,
        "success"
      );
      showCreateBucketModal = false;
      newBucketName = "";
      selectedFile = null;
      bucketMetadataString = "";
      bucketMetadata = {};
      currentPage = 1;
      gridfsResponse.buckets = []; // Clear cache to force refetch
      await fetchGridFSBuckets();
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Toggles the stats popover for a GridFS bucket.
   */
  async function toggleStats(bucketOpaqueId: string) {
    if (showStatsPopover === bucketOpaqueId) {
      // Close popover
      showStatsPopover = null;
      statsData = null;
      statsLoading = false;
      return;
    }

    // Open popover and fetch stats if not already loaded
    showStatsPopover = bucketOpaqueId;

    if (!statsCache[bucketOpaqueId]) {
      statsLoading = true;
      loadingStats[bucketOpaqueId] = true;
      loadingStats = { ...loadingStats }; // Trigger reactivity
      statsData = null;

      try {
        const response = await api.apiGet<any>(
          `/db/${db}/gridfs/${bucketOpaqueId}/stats`
        );
        statsCache[bucketOpaqueId] = response;
        statsData = response;
      } catch (e) {
        addNotification(
          `Failed to load stats: ${e instanceof Error ? e.message : String(e)}`,
          "error"
        );
        showStatsPopover = null;
      } finally {
        statsLoading = false;
        loadingStats[bucketOpaqueId] = false;
        loadingStats = { ...loadingStats }; // Trigger reactivity
      }
    } else {
      // Use cached data
      statsData = statsCache[bucketOpaqueId];
      statsLoading = false;
    }
  }

  /**
   * Copies bucket name to clipboard with visual feedback.
   */
  async function copyBucketName(bucketName: string) {
    try {
      await navigator.clipboard.writeText(bucketName);
      justCopied = bucketName;
      setTimeout(() => {
        justCopied = null;
      }, 200);
    } catch (err) {
      console.error("Failed to copy bucket name:", err);
    }
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
      {:else if gridfsResponse.buckets.length === 0}
        <div
          class="text-center text-secondary/60 h-full flex flex-col justify-center items-center"
        >
          <p class="text-2xl font-semibold poppins">No buckets available</p>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-1 p-1">
          {#each gridfsResponse.buckets as bucket, index (bucket.opaque_id)}
            {@const isLastRow = index >= gridfsResponse.buckets.length - 4}
            {@const hasTooltip = overflowingBuckets.has(bucket.bucket_name)}
            <div
              class="card group shadow-sm cursor-pointer hover:bg-neutral/20 transition-all duration-200 ease-in-out h-14 {hasTooltip
                ? `tooltip ${isLastRow ? 'tooltip-top' : 'tooltip-bottom'}`
                : ''}"
              data-tip={hasTooltip ? bucket.bucket_name : null}
              role="button"
              tabindex="0"
              on:click={() => handleBucketClick(bucket)}
              on:keydown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleBucketClick(bucket);
                }
              }}
              style="position: relative;"
            >
              <div
                class="card-body px-2 py-1 flex-row justify-between items-center"
              >
                <div class="flex-1 mr-3 overflow-hidden" style="min-width: 0;">
                  <span
                    use:checkTextOverflow={bucket.bucket_name}
                    class="card-title text-base poppins font-normal transition-colors duration-200 block overflow-hidden text-ellipsis whitespace-nowrap"
                  >
                    {bucket.bucket_name}
                  </span>
                </div>
                <div class="flex items-center gap-0.5 flex-shrink-0 relative">
                  <div class="relative">
                    <button
                      on:click|stopPropagation={() =>
                        toggleStats(bucket.opaque_id)}
                      class="tooltip tooltip-left hover:text-info px-2 rounded-full cursor-pointer"
                      data-tip={`View Stats`}
                      aria-label={`View stats for ${bucket.bucket_name}`}
                    >
                      <i class="fas fa-chart-bar"></i>
                    </button>
                    {#if showStatsPopover === bucket.opaque_id}
                      <div
                        in:fade={{ duration: 200 }}
                        out:fade={{ duration: 200 }}
                      >
                        <StatsPopover
                          data={statsData}
                          loading={loadingStats[bucket.opaque_id] || false}
                          showPopover={true}
                          rowIndex={index}
                          totalRows={gridfsResponse.buckets.length}
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
                      copyBucketName(bucket.bucket_name)}
                    class="tooltip tooltip-left hover:text-primary px-2 rounded-full cursor-pointer"
                    data-tip={`Copy`}
                    aria-label={`Copy bucket name ${bucket.bucket_name}`}
                  >
                    <i
                      class="{justCopied === bucket.bucket_name
                        ? 'fa-solid'
                        : 'fa-regular'} fa-copy"
                    ></i>
                  </button>
                  <button
                    on:click|stopPropagation={() => {
                      bucketToDelete = bucket.opaque_id;
                      bucketToDeleteName = bucket.bucket_name;
                      showDeleteBucketModal = true;
                    }}
                    class="tooltip tooltip-left {isProtectedBucket(
                      gridfsResponse.database?.name || ''
                    )
                      ? 'text-base-content/30 cursor-not-allowed'
                      : 'hover:text-error cursor-pointer'} px-2 rounded-full"
                    data-tip={isProtectedBucket(
                      gridfsResponse.database?.name || ""
                    )
                      ? "Cannot delete protected bucket"
                      : "Delete"}
                    aria-label={`Delete bucket ${bucket.bucket_name}`}
                    disabled={isProtectedBucket(
                      gridfsResponse.database?.name || ""
                    )}
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
  title="Confirm Bucket Deletion"
  message={`Are you sure you want to delete the GridFS bucket "${bucketToDeleteName}"? This action cannot be undone.`}
  onConfirm={confirmDeleteBucket}
  onCancel={cancelDeleteBucket}
  show={showDeleteBucketModal}
/>

<Modal
  title="Create New GridFS Bucket"
  message=""
  onConfirm={handleCreateBucket}
  onCancel={() => {
    showCreateBucketModal = false;
    newBucketName = "";
    selectedFile = null;
    bucketMetadata = {};
  }}
  confirmButtonText="Create"
  cancelButtonText="Cancel"
  show={showCreateBucketModal}
>
  <div class="space-y-4">
    <div class="form-control">
      <label class="label" for="newBucketName">
        <span class="label-text">Bucket Name</span>
      </label>
      <input
        type="text"
        id="newBucketName"
        bind:value={newBucketName}
        placeholder="Enter bucket name"
        class="input input-bordered w-full"
      />
    </div>

    <div class="form-control">
      <label class="label" for="bucketFile">
        <span class="label-text"
          >File to Upload
          <div
            class="tooltip tooltip-right"
            data-tip="Initial file upload is required to create a bucket. Max size: 100MB."
          >
            <i class="fas fa-info-circle text-accent text-sm cursor-help"></i>
          </div>
        </span>
      </label>
      <input
        type="file"
        id="bucketFile"
        on:change={handleFileSelect}
        class="file-input w-full"
      />
    </div>

    <div class="form-control">
      <label class="label" for="bucketMetadata">
        <span class="label-text">Metadata (JSON)</span>
      </label>
      <textarea
        id="bucketMetadata"
        bind:value={bucketMetadataString}
        placeholder={`{"key": "value"}`}
        class="textarea textarea-bordered w-full h-24"
      ></textarea>
    </div>
  </div>
</Modal>

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }

  /* Custom tooltip styles for long bucket names */
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
