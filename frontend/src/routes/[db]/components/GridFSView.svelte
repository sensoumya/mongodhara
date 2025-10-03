<script lang="ts">
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import type { PaginatedGridFSBuckets } from "$lib/stores/types";
  import { fade } from "svelte/transition";

  export let db: string;
  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let loading: boolean = false;
  let error: boolean = false;

  const pageSize: number = 16;

  export let gridfsResponse: PaginatedGridFSBuckets = {
    buckets: [],
    total: 0,
    page: 1,
    page_size: 16,
  };

  let showDeleteBucketModal = false;
  let bucketToDelete: string | null = null;
  let showCreateBucketModal = false;
  let newBucketName: string = "";
  let selectedFile: File | null = null;
  let bucketMetadataString: string = "";
  let bucketMetadata: Record<string, any> = {};

  // Computed validation state for create bucket
  $: createBucketValid = newBucketName.trim() !== "" && selectedFile !== null;
  $: bucketValidationMessage =
    !newBucketName.trim() && !selectedFile
      ? "Please fill in Bucket Name and select a file"
      : !newBucketName.trim()
        ? "Please fill in Bucket Name"
        : !selectedFile
          ? "Please select a file to upload"
          : "";

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

  /**
   * Navigates to the GridFS bucket detail page.
   * @param bucketName The name of the bucket to navigate to.
   */
  function handleBucketClick(bucketName: string) {
    goto(`${base}/${db}/${bucketName}?type=gridfs`);
  }

  /**
   * Fetches the list of GridFS buckets for the current database.
   */
  export async function fetchGridFSBuckets() {
    loading = true;
    error = false;
    try {
      const query = new URLSearchParams();

      if (searchTerm.trim() !== "") {
        query.append("search", searchTerm);
      }

      query.append("page", currentPage.toString());
      query.append("page_size", pageSize.toString());

      const response = await api.apiGet<PaginatedGridFSBuckets>(
        `/db/${db}/gridfs/buckets?${query.toString()}`
      );
      gridfsResponse = response;
    } catch (e) {
      error = true;
      addNotification(e.message, "error");
      gridfsResponse = {
        buckets: [],
        total: 0,
        page: 1,
        page_size: 16,
      };
    } finally {
      loading = false;
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
      addNotification(
        `Bucket "${bucketToDelete}" deleted successfully.`,
        "success"
      );
      await fetchGridFSBuckets();
    } catch (e) {
      addNotification(e.message, "error");
    } finally {
      showDeleteBucketModal = false;
      bucketToDelete = null;
    }
  }

  /**
   * Cancels the bucket deletion.
   */
  function cancelDeleteBucket() {
    showDeleteBucketModal = false;
    bucketToDelete = null;
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
    if (!createBucketValid) return;

    try {
      const formData = new FormData();
      formData.append("file", selectedFile!);

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
        `/db/${db}/gridfs/${newBucketName}/upload`,
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
      await fetchGridFSBuckets();
    } catch (e) {
      addNotification(e.message, "error");
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
      {:else if gridfsResponse.buckets.length === 0}
        <div
          class="text-center text-secondary/40 h-full flex flex-col justify-center items-center"
        >
          <p class="text-2xl font-semibold poppins">No content available</p>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-1">
          {#each gridfsResponse.buckets as bucket, index (bucket.bucket_name)}
            {@const rowNumber = Math.floor(index / 2) + 1}
            {@const isLastRow = rowNumber === 8}
            {@const hasTooltip = overflowingBuckets.has(bucket.bucket_name)}
            <div
              class="card group shadow-lg cursor-pointer hover:bg-neutral/20 hover:shadow-xl transition-all duration-200 ease-in-out h-14 {hasTooltip
                ? `tooltip ${isLastRow ? 'tooltip-top' : 'tooltip-bottom'}`
                : ''}"
              data-tip={hasTooltip ? bucket.bucket_name : null}
              role="button"
              tabindex="0"
              on:click={() => handleBucketClick(bucket.bucket_name)}
              on:keydown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleBucketClick(bucket.bucket_name);
                }
              }}
              style="position: relative;"
            >
              <div class="card-body p-3 flex-row justify-between items-center">
                <div class="flex-1 mr-3 overflow-hidden" style="min-width: 0;">
                  <span
                    use:checkTextOverflow={bucket.bucket_name}
                    class="card-title text-l poppins font-normal block overflow-hidden text-ellipsis whitespace-nowrap"
                  >
                    {bucket.bucket_name}
                  </span>
                </div>
                <div class="flex items-center space-x-2 flex-shrink-0">
                  <div
                    class="w-6 h-6 rounded-full bg-accent text-accent-content text-xs font-medium flex items-center justify-center"
                  >
                    {bucket.files_count}
                  </div>
                  <button
                    on:click|stopPropagation={() =>
                      handleDeleteBucketClick(bucket.bucket_name)}
                    class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                    data-tip={`Delete`}
                    aria-label={`Delete bucket ${bucket.bucket_name}`}
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

{#if showDeleteBucketModal}
  <Modal
    title="Confirm Bucket Deletion"
    message={`Are you sure you want to delete the GridFS bucket "${bucketToDelete}"? This action cannot be undone.`}
    onConfirm={confirmDeleteBucket}
    onCancel={cancelDeleteBucket}
  />
{/if}

{#if showCreateBucketModal}
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
    confirmDisabled={!createBucketValid}
    validationMessage={bucketValidationMessage}
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
          class="input input-bordered w-full input-secondary"
        />
      </div>

      <div class="form-control">
        <label class="label" for="bucketFile">
          <span class="label-text"
            >File to Upload
            <div
              class="tooltip tooltip-right"
              data-tip="Initial file upload is required to create a bucket"
            >
              <i class="fas fa-info-circle text-accent text-sm cursor-help"></i>
            </div>
          </span>
        </label>
        <input
          type="file"
          id="bucketFile"
          on:change={handleFileSelect}
          class="file-input file-input-bordered file-input-secondary w-full"
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
          class="textarea textarea-bordered w-full h-24 input-secondary"
        ></textarea>
      </div>
    </div>
  </Modal>
{/if}

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
