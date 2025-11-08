<script lang="ts">
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import { fade } from "svelte/transition";
  import DatabaseGrantsEditor from "./DatabaseGrantsEditor.svelte";
  import SimpleModal from "./SimpleModal.svelte";

  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let pageSize: number = 20;

  export let groupsResponse: any = { groups: [], total: 0 };
  export let totalPages = 1;

  let isLoading: boolean = false;
  let error: boolean = false;

  // Modal states
  let showDeleteModal = false;
  let groupToDelete: string | null = null;
  let showCreateModal = false;
  let showEditModal = false;
  let groupToEdit: any = null;

  // Form data
  let newGroupName: string = "";
  let newGroupDescription: string = "";
  let newGroupGrants: Record<
    string,
    { r: boolean; w: boolean; d: boolean; a: boolean }
  > = {};

  $: totalPages = Math.ceil(groupsResponse.total / pageSize);

  /**
   * Fetches permission groups with pagination
   */
  export async function fetchGroups(forceRefresh: boolean = false) {
    if (!forceRefresh && groupsResponse.groups.length > 0) {
      return;
    }

    isLoading = true;
    error = false;
    try {
      const skip = (currentPage - 1) * pageSize;
      const response = await api.apiGet<any>(
        `/admin/groups?skip=${skip}&limit=${pageSize}`
      );

      // Filter locally if search term is present
      let filteredGroups = response;
      if (searchTerm.trim()) {
        filteredGroups = response.filter(
          (g: any) =>
            g.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            g.description.toLowerCase().includes(searchTerm.toLowerCase())
        );
      }

      groupsResponse = {
        groups: filteredGroups,
        total: filteredGroups.length,
      };
    } catch (e) {
      error = true;
      groupsResponse = { groups: [], total: 0 };
      addNotification(e instanceof Error ? e.message : String(e), "error");
    } finally {
      isLoading = false;
    }
  }

  /**
   * Show create group modal
   */
  export function showCreateGroupModal() {
    newGroupName = "";
    newGroupDescription = "";
    newGroupGrants = {};
    showCreateModal = true;
  }

  /**
   * Create new permission group
   */
  async function createGroup() {
    try {
      await api.apiPost("/admin/groups", {
        name: newGroupName,
        description: newGroupDescription,
        grants: newGroupGrants,
      });

      addNotification(
        `Group "${newGroupName}" created successfully`,
        "success"
      );
      showCreateModal = false;
      await fetchGroups(true);
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Open edit modal
   */
  function handleEditClick(group: any) {
    groupToEdit = { ...group };
    newGroupDescription = group.description;
    newGroupGrants = { ...group.grants };
    showEditModal = true;
  }

  /**
   * Update existing permission group
   */
  async function updateGroup() {
    if (!groupToEdit) return;

    try {
      await api.apiPut(`/admin/groups/${groupToEdit.name}`, {
        description: newGroupDescription,
        grants: newGroupGrants,
      });

      addNotification(
        `Group "${groupToEdit.name}" updated successfully`,
        "success"
      );
      showEditModal = false;
      await fetchGroups(true);
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Confirm delete
   */
  async function confirmDelete() {
    if (!groupToDelete) return;

    try {
      await api.apiDelete(`/admin/groups/${groupToDelete}`);
      addNotification(
        `Group "${groupToDelete}" deleted successfully`,
        "success"
      );
      showDeleteModal = false;
      groupToDelete = null;
      await fetchGroups(true);
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Format grants for display
   */
  function formatGrants(grants: any): string {
    const dbCount = Object.keys(grants).length;
    return `${dbCount} database${dbCount !== 1 ? "s" : ""}`;
  }
</script>

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
{:else if error}
  <div
    class="text-center text-secondary/60 h-full flex flex-col justify-center items-center"
  >
    <p class="text-2xl font-semibold poppins">Unable to load content</p>
  </div>
{:else if groupsResponse.groups.length === 0}
  <div
    class="text-center text-secondary/60 h-full flex flex-col justify-center items-center"
  >
    <p class="text-2xl font-semibold poppins">No content available</p>
  </div>
{:else}
  <div class="overflow-x-auto rounded-box">
    <table class="table table-zebra w-full">
      <thead>
        <tr class="bg-primary/40">
          <th>Name</th>
          <th>Description</th>
          <th>Grants</th>
          <th>Created</th>
          <th>Updated</th>
          <th class="text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each groupsResponse.groups as group (group.name)}
          <tr transition:fade={{ duration: 200 }}>
            <td class="font-semibold">
              {group.name}
            </td>
            <td class="max-w-xs truncate" title={group.description}>
              {group.description}
            </td>
            <td class="max-w-xs">
              <div class="flex flex-wrap gap-1">
                {#each Object.keys(group.grants) as pattern}
                  <span
                    class="badge badge-soft badge-primary badge-sm cursor-help"
                    title="Database pattern: {pattern}"
                  >
                    {pattern}
                  </span>
                {/each}
                {#if Object.keys(group.grants).length === 0}
                  <span class="text-base-content/50 text-sm">No grants</span>
                {/if}
              </div>
            </td>
            <td class="text-sm text-base-content/70">
              {new Date(group.created_at).toLocaleString()}
            </td>
            <td class="text-sm text-base-content/70">
              {new Date(group.updated_at).toLocaleString()}
            </td>
            <td class="text-right">
              <div class="flex gap-2 justify-end">
                <button
                  class="tooltip tooltip-left hover:text-secondary px-2 rounded-full cursor-pointer"
                  on:click={() => handleEditClick(group)}
                  title="Edit group"
                  aria-label="Edit group"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button
                  class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                  on:click={() => {
                    groupToDelete = group.name;
                    showDeleteModal = true;
                  }}
                  title="Delete group"
                  aria-label="Delete group"
                >
                  <i class="fas fa-trash-alt"></i>
                </button>
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<!-- Create Group Modal -->
<SimpleModal bind:show={showCreateModal}>
  <h3
    class="text-lg poppins mb-6 text-center flex items-center justify-center gap-4"
  >
    Create Permission Group
  </h3>
  <div class="space-y-4 px-1">
    <div>
      <div class="label">
        <span class="label-text">
          Group Name
          <span class="text-error">*</span>
        </span>
      </div>
      <input
        type="text"
        bind:value={newGroupName}
        placeholder="e.g., developers, admins"
        class="input input-bordered w-full"
      />
    </div>
    <DatabaseGrantsEditor
      bind:description={newGroupDescription}
      bind:grants={newGroupGrants}
      allowAdmin={false}
    />
  </div>
  <div class="modal-action">
    <button class="btn" on:click={() => (showCreateModal = false)}
      >Cancel</button
    >
    <button
      class="btn btn-primary"
      on:click={createGroup}
      disabled={!newGroupName || !newGroupDescription}
    >
      Create Group
    </button>
  </div>
</SimpleModal>

<!-- Edit Group Modal -->
<SimpleModal bind:show={showEditModal}>
  <h3
    class="text-lg poppins mb-6 text-center flex items-center justify-center gap-4"
  >
    Edit Group: "{groupToEdit?.name}"
  </h3>
  <div class="px-1">
    <DatabaseGrantsEditor
      bind:description={newGroupDescription}
      bind:grants={newGroupGrants}
      allowAdmin={false}
    />
  </div>
  <div class="modal-action">
    <button class="btn" on:click={() => (showEditModal = false)}>Cancel</button>
    <button class="btn btn-primary" on:click={updateGroup}>
      Update Group
    </button>
  </div>
</SimpleModal>

<!-- Delete Confirmation Modal -->
<Modal
  title="Delete Permission Group"
  message={`Are you sure you want to delete the group "${groupToDelete}"? This action cannot be undone.`}
  onConfirm={confirmDelete}
  onCancel={() => (showDeleteModal = false)}
  confirmButtonText="Delete"
  cancelButtonText="Cancel"
  bind:show={showDeleteModal}
/>
