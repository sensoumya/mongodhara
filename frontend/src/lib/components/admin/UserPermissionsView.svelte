<script lang="ts">
  import Modal from "$lib/components/Modal.svelte";
  import * as api from "$lib/stores/api";
  import { addNotification } from "$lib/stores/notifications";
  import { fade } from "svelte/transition";
  import DatabaseGrantsEditor from "./DatabaseGrantsEditor.svelte";
  import MultiSelectDropdown from "./MultiSelectDropdown.svelte";
  import SimpleModal from "./SimpleModal.svelte";
  import TagInput from "./TagInput.svelte";

  export let searchTerm: string = "";
  export let currentPage: number = 1;
  export let pageSize: number = 20;

  export let usersResponse: any = { users: [], total: 0 };
  export let totalPages = 1;

  let isLoading: boolean = false;
  let error: boolean = false;

  // Modal states
  let showDeleteModal = false;
  let userToDelete: string | null = null;
  let showCreateModal = false;
  let showEditModal = false;
  let userToEdit: any = null;

  // Form data
  let userEmails: string[] = [];
  let selectedRole: string = "user";
  let selectedGroups: string[] = [];
  let customGrants: Record<
    string,
    { r: boolean; w: boolean; d: boolean; a: boolean }
  > = {};
  let isActive: boolean = true;

  // Available groups (fetch on mount)
  let availableGroups: any[] = [];

  $: totalPages = Math.ceil(usersResponse.total / pageSize);

  /**
   * Fetches user permissions with pagination
   */
  export async function fetchUsers(forceRefresh: boolean = false) {
    if (!forceRefresh && usersResponse.users.length > 0) {
      return;
    }

    isLoading = true;
    error = false;
    try {
      const skip = (currentPage - 1) * pageSize;
      const response = await api.apiGet<any>(
        `/admin/users?skip=${skip}&limit=${pageSize}`
      );

      // Filter locally if search term is present
      let filteredUsers = response;
      if (searchTerm.trim()) {
        filteredUsers = response.filter((u: any) =>
          u.email.toLowerCase().includes(searchTerm.toLowerCase())
        );
      }

      usersResponse = {
        users: filteredUsers,
        total: filteredUsers.length,
      };
    } catch (e) {
      error = true;
      usersResponse = { users: [], total: 0 };
      addNotification(e instanceof Error ? e.message : String(e), "error");
    } finally {
      isLoading = false;
    }
  }

  /**
   * Fetch available groups for dropdown
   */
  async function fetchAvailableGroups() {
    try {
      availableGroups = await api.apiGet<any[]>(
        "/admin/groups?skip=0&limit=1000"
      );
    } catch (e) {
      addNotification("Failed to load available groups", "error");
    }
  }

  /**
   * Show create user modal
   */
  export async function showCreateUserModal() {
    await fetchAvailableGroups();
    userEmails = [];
    selectedRole = "user";
    selectedGroups = [];
    customGrants = {};
    showCreateModal = true;
  }

  /**
   * Create new user permission
   */
  async function createUser() {
    try {
      // Create users in batch
      for (const email of userEmails) {
        await api.apiPost("/admin/users", {
          email: email,
          role: selectedRole,
          groups: selectedGroups,
          custom_grants: customGrants,
        });
      }

      addNotification(
        `${userEmails.length} user(s) created successfully`,
        "success"
      );
      showCreateModal = false;
      await fetchUsers(true);
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Open edit modal
   */
  async function handleEditClick(user: any) {
    await fetchAvailableGroups();
    userToEdit = { ...user };
    selectedRole = user.role || "user";
    selectedGroups = user.groups || [];
    customGrants = user.custom_grants || {};
    isActive = user.isActive;
    showEditModal = true;
  }

  /**
   * Update user permission
   */
  async function updateUser() {
    if (!userToEdit) return;

    try {
      await api.apiPut(`/admin/users/${userToEdit.email}`, {
        role: selectedRole,
        groups: selectedGroups,
        custom_grants: customGrants,
        isActive: isActive,
      });

      addNotification(
        `User "${userToEdit.email}" updated successfully`,
        "success"
      );
      showEditModal = false;
      await fetchUsers(true);
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
  }

  /**
   * Confirm delete
   */
  async function confirmDelete() {
    if (!userToDelete) return;

    try {
      await api.apiDelete(`/admin/users/${userToDelete}`);
      addNotification(`User "${userToDelete}" deleted successfully`, "success");
      showDeleteModal = false;
      userToDelete = null;
      await fetchUsers(true);
    } catch (e) {
      addNotification(e instanceof Error ? e.message : String(e), "error");
    }
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
{:else if usersResponse.users.length === 0}
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
          <th>Email</th>
          <th>Role</th>
          <th>Groups</th>
          <th>Custom Grants</th>
          <th>Status</th>
          <th>Created</th>
          <th class="text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each usersResponse.users as user (user.email)}
          <tr transition:fade={{ duration: 200 }}>
            <td class="font-semibold">
              {user.email}
            </td>
            <td>
              <span
                class={`badge badge-soft badge-sm ${
                  user.role === "admin" ? "badge-warning" : "badge-info"
                }`}
              >
                {user.role || "user"}
              </span>
            </td>
            <td>
              <div class="flex flex-wrap gap-1">
                {#each user.groups as group}
                  <span class="badge badge-primary badge-soft badge-sm"
                    >{group}</span
                  >
                {/each}
                {#if user.groups.length === 0}
                  <span class="text-base-content/50 text-sm">No groups</span>
                {/if}
              </div>
            </td>
            <td>
              {#if Object.keys(user.custom_grants || {}).length > 0}
                <span class="badge badge-secondary badge-soft badge-sm">
                  {Object.keys(user.custom_grants).length}
                </span>
              {:else}
                <span class="badge badge-soft badge-sm">
                  {Object.keys(user.custom_grants).length}
                </span>
              {/if}
            </td>
            <td>
              {#if user.isActive}
                <span class="badge badge-soft badge-success badge-sm"
                  >Active</span
                >
              {:else}
                <span class="badge badge-soft badge-error badge-sm"
                  >Inactive</span
                >
              {/if}
            </td>
            <td class="text-sm text-base-content/70">
              {new Date(user.created_at).toLocaleString()}
            </td>
            <td class="text-right">
              <div class="flex gap-2 justify-end">
                <button
                  class="tooltip tooltip-left hover:text-secondary px-2 rounded-full cursor-pointer"
                  on:click={() => handleEditClick(user)}
                  aria-label="Edit user"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button
                  class="tooltip tooltip-left hover:text-error px-2 rounded-full cursor-pointer"
                  on:click={() => {
                    userToDelete = user.email;
                    showDeleteModal = true;
                  }}
                  aria-label="Delete user"
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

<!-- Create User Modal -->
<SimpleModal bind:show={showCreateModal} maxWidth="max-w-4xl">
  <div class="flex flex-col h-full">
    <h3
      class="text-lg poppins mb-6 text-center flex items-center justify-center gap-4"
    >
      Create User Permission
    </h3>

    <div class="flex-1 overflow-y-auto space-y-4 px-1 min-h-0">
      <div>
        <div class="label">
          <span class="label-text">
            User Email(s)
            <span class="text-error">*</span>
          </span>
        </div>
        <TagInput
          bind:tags={userEmails}
          placeholder="Enter email and press Enter"
          validate={(email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)}
          errorMessage="Please enter a valid email address"
        />
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="label">
            <span class="label-text">Role</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm">User</span>
            <input
              type="checkbox"
              class="toggle toggle-primary"
              checked={selectedRole === "admin"}
              on:change={(e) =>
                (selectedRole = e.target.checked ? "admin" : "user")}
            />
            <span class="text-sm">Admin</span>
          </div>
        </div>
        <div>
          <div class="label">
            <span class="label-text">
              Assign Group(s)
              {#if selectedRole === "user"}
                <span class="text-error">*</span>
              {/if}
            </span>
          </div>
          <MultiSelectDropdown
            bind:selected={selectedGroups}
            options={availableGroups.map((g) => ({
              value: g.name,
              label: g.name,
              description: g.description || "",
            }))}
            placeholder="Select groups..."
          />
        </div>
      </div>
      <div>
        <DatabaseGrantsEditor
          bind:grants={customGrants}
          title="Custom Grants"
          description={undefined}
        />
      </div>
    </div>
    <div class="modal-action mt-4">
      <button class="btn" on:click={() => (showCreateModal = false)}
        >Cancel</button
      >
      <button
        class="btn btn-primary"
        on:click={createUser}
        disabled={userEmails.length === 0 ||
          (selectedRole === "user" && selectedGroups.length === 0)}
      >
        Add User
      </button>
    </div>
  </div>
</SimpleModal>

<!-- Edit User Modal -->
<SimpleModal bind:show={showEditModal} maxWidth="max-w-4xl">
  <div class="flex flex-col h-full">
    <h3
      class="text-lg poppins mb-6 text-center flex items-center justify-center gap-4"
    >
      Edit User: "{userToEdit?.email}"
    </h3>
    <div class="flex-1 overflow-y-auto space-y-4 px-1 min-h-0">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="label">
            <span class="label-text">Role</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm">User</span>
            <input
              type="checkbox"
              class="toggle toggle-primary"
              checked={selectedRole === "admin"}
              on:change={(e) =>
                (selectedRole = e.target.checked ? "admin" : "user")}
            />
            <span class="text-sm">Admin</span>
          </div>
        </div>
        <div>
          <div class="label">
            <span class="label-text">Assign Group(s)</span>
          </div>
          <MultiSelectDropdown
            bind:selected={selectedGroups}
            options={availableGroups.map((g) => ({
              value: g.name,
              label: g.name,
              description: g.description || "",
            }))}
            placeholder="Select groups..."
          />
        </div>
      </div>
      <div>
        <DatabaseGrantsEditor
          bind:grants={customGrants}
          title="Custom Grants"
          description={undefined}
        />
      </div>
      <div>
        <label class="label cursor-pointer">
          <span class="label-text">Active Status</span>
          <input
            type="checkbox"
            class="toggle toggle-secondary"
            bind:checked={isActive}
          />
        </label>
      </div>
    </div>
    <div class="modal-action mt-4">
      <button class="btn" on:click={() => (showEditModal = false)}
        >Cancel</button
      >
      <button class="btn btn-primary" on:click={updateUser}>
        Update User
      </button>
    </div>
  </div>
</SimpleModal>

<!-- Delete Confirmation Modal -->
<Modal
  title="Delete User Permission"
  message={`Are you sure you want to delete permissions for "${userToDelete}"? This action cannot be undone.`}
  onConfirm={confirmDelete}
  onCancel={() => (showDeleteModal = false)}
  confirmButtonText="Delete"
  cancelButtonText="Cancel"
  bind:show={showDeleteModal}
/>
