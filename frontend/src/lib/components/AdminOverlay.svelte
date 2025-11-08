<script lang="ts">
  import { tick } from "svelte";
  import { fade, fly } from "svelte/transition";
  import PermissionGroupsView from "./admin/PermissionGroupsView.svelte";
  import UserPermissionsView from "./admin/UserPermissionsView.svelte";
  import Pagination from "./Pagination.svelte";

  export let show: boolean = false;

  let carouselIndex: number = 0;
  let searchTerm: string = "";
  let currentPage: number = 1;
  let totalPages: number = 1;
  let pageSize: number =
    typeof window !== "undefined"
      ? parseInt(localStorage.getItem("pageSize_admin") || "20")
      : 20;
  let contentReady: boolean = false;

  // Component references
  let permissionGroupsView: PermissionGroupsView;
  let userPermissionsView: UserPermissionsView;

  // Loading state for search operations
  let isLoading: boolean = false;

  // Response data from components
  let groupsResponse: any = { groups: [], total: 0 };
  let usersResponse: any = { users: [], total: 0 };

  // Save pageSize to localStorage whenever it changes
  $: if (typeof window !== "undefined") {
    localStorage.setItem("pageSize_admin", pageSize.toString());
  }

  $: placeholder =
    carouselIndex === 0
      ? "Search users..."
      : carouselIndex === 1
        ? "Search permission groups..."
        : "Search configs...";

  /**
   * Handles carousel navigation and data fetching.
   */
  function handleCarouselChange(index: number) {
    carouselIndex = index;
    currentPage = 1;
    searchTerm = "";

    setTimeout(() => {
      fetchData();
    }, 0);
  }

  /**
   * Handles search operations.
   */
  function handleSearch() {
    currentPage = 1;
    fetchData();
  }

  /**
   * Handles form submission for search.
   */
  function handleSearchSubmit() {
    currentPage = 1;
    fetchData(true);
  }

  /**
   * Fetches data based on current carousel index.
   */
  async function fetchData(forceRefresh: boolean = false) {
    isLoading = true;
    try {
      if (carouselIndex === 0) {
        if (userPermissionsView) {
          await userPermissionsView.fetchUsers(forceRefresh);
        }
      } else if (carouselIndex === 1) {
        if (permissionGroupsView) {
          await permissionGroupsView.fetchGroups(forceRefresh);
        }
      }
      // carouselIndex === 2 (Configs) - no data to fetch yet
    } finally {
      isLoading = false;
    }
  }

  /**
   * Handles page changes from the pagination component.
   */
  function handlePageChange(event: CustomEvent<{ page: number }>) {
    currentPage = event.detail.page;
    fetchData(true);
  }

  /**
   * Handles Create button click.
   */
  function handleCreate() {
    if (carouselIndex === 0) {
      userPermissionsView?.showCreateUserModal();
    } else if (carouselIndex === 1) {
      permissionGroupsView?.showCreateGroupModal();
    }
    // carouselIndex === 2 (Configs) - no create action yet
  }

  /**
   * Close overlay
   */
  function closeOverlay() {
    show = false;
  }

  /**
   * Handle escape key to close
   */
  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && show) {
      closeOverlay();
    }
  }

  /**
   * Fetch initial data when overlay opens
   */
  $: if (show) {
    contentReady = true; // Show overlay immediately
  } else {
    contentReady = false;
  }

  /**
   * Fetch data after overlay is shown and components are mounted
   */
  $: if (show && contentReady) {
    (async () => {
      await tick(); // Wait for components to mount
      await fetchData(true);
    })();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show && contentReady}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm"
    on:click={closeOverlay}
    transition:fade={{ duration: 200 }}
  ></div>

  <!-- Modal Container -->
  <div
    class="fixed inset-8 md:inset-16 lg:inset-24 xl:inset-32 z-50 flex items-center justify-center"
    transition:fly={{ y: 20, duration: 300 }}
  >
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
      class="bg-base-100 rounded-lg shadow-2xl w-full h-full flex flex-col overflow-hidden"
      on:click|stopPropagation
    >
      <!-- Close Button -->
      <div class="flex justify-end p-4 pb-0">
        <button
          class="btn btn-circle btn-sm btn-ghost hover:text-error hover:bg-transparent hover:border-transparent"
          on:click={closeOverlay}
          aria-label="Close admin overlay"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="flex flex-col flex-grow overflow-hidden px-4 pb-2">
        <!-- Carousel Tabs (Same style as Collections/GridFS) -->
        <div class="w-full">
          <h1
            class="text-2xl poppins mb-4 text-center flex items-center justify-center gap-4"
          >
            <button
              class="flex items-center gap-2 transition-all duration-200 {carouselIndex ===
              0
                ? 'cursor-default'
                : 'text-base opacity-30 hover:opacity-60 cursor-pointer'}"
              on:click={() => carouselIndex !== 0 && handleCarouselChange(0)}
              disabled={carouselIndex === 0}
            >
              <i class="fas fa-user-shield text-primary"></i>
              <span>Users</span>
            </button>
            <div class="divider divider-horizontal mx-0"></div>
            <button
              class="flex items-center gap-2 transition-all duration-200 {carouselIndex ===
              1
                ? 'cursor-default'
                : 'text-base opacity-30 hover:opacity-60 cursor-pointer'}"
              on:click={() => carouselIndex !== 1 && handleCarouselChange(1)}
              disabled={carouselIndex === 1}
            >
              <i class="fas fa-users-cog text-primary"></i>
              <span>Groups</span>
            </button>
          </h1>
        </div>

        <!-- Search and Create Controls -->
        <div class="flex justify-end items-center gap-2 mb-2">
          <form
            on:submit|preventDefault={handleSearchSubmit}
            class="flex w-full max-w-xs"
          >
            <label
              class="input input-ghost input-sm flex items-center gap-2 w-full focus-within:outline-none"
            >
              <input
                type="text"
                class="text-base outline-none"
                bind:value={searchTerm}
                {placeholder}
              />
              <div class="flex items-center w-6">
                {#if searchTerm}
                  <button
                    type="button"
                    on:click={() => {
                      searchTerm = "";
                      handleSearchSubmit();
                    }}
                    class="btn btn-sm btn-ghost btn-circle"
                    disabled={isLoading}
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
                disabled={isLoading}
                aria-label={searchTerm ? "Search" : "Reload"}
              >
                <i class="fas {searchTerm ? 'fa-search' : 'fa-rotate-right'}"
                ></i>
              </button>
            </label>
          </form>
          {#if carouselIndex !== 2}
            <button
              on:click={handleCreate}
              class="btn btn-secondary btn-sm flex items-center gap-1"
              aria-label={carouselIndex === 0
                ? "Create user permission"
                : "Create permission group"}
            >
              <i class="fas fa-plus"></i>
              <span class="hidden md:inline">Add</span>
            </button>
          {/if}
        </div>

        <!-- Separator line -->
        <div class="border-t border-base-content/10 mb-2"></div>

        <!-- Main Content Area -->
        <div class="flex-grow overflow-y-auto mb-4 relative">
          {#if carouselIndex === 0}
            <UserPermissionsView
              bind:this={userPermissionsView}
              bind:usersResponse
              bind:totalPages
              {searchTerm}
              {currentPage}
              {pageSize}
            />
          {:else if carouselIndex === 1}
            <PermissionGroupsView
              bind:this={permissionGroupsView}
              bind:groupsResponse
              bind:totalPages
              {searchTerm}
              {currentPage}
              {pageSize}
            />
          {:else}
            <!-- Configs Tab - Coming Soon -->
            <div
              class="text-center text-secondary/40 h-full flex flex-col justify-center items-center"
            >
              <p class="text-2xl font-semibold poppins">
                Configuration management coming soon
              </p>
            </div>
          {/if}
        </div>

        <!-- Pagination Controls -->
        <Pagination
          {currentPage}
          {totalPages}
          loading={false}
          {pageSize}
          showPageSize={true}
          on:pageChange={handlePageChange}
          on:pageSizeChange={(e) => {
            pageSize = e.detail.pageSize;
            currentPage = 1;
            fetchData(true);
          }}
        />
      </div>
    </div>
  </div>
{/if}

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }
</style>
