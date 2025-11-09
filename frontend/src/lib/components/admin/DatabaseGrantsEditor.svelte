<script lang="ts">
  import * as api from "$lib/stores/api";
  import { onMount } from "svelte";

  export let grants: Record<
    string,
    { r: boolean; w: boolean; d: boolean; a: boolean }
  > = {};
  export let description: string | undefined = undefined;
  export let title: string = "Database Grants";
  export let allowAdmin: boolean = true;

  let newDbName: string = "";
  let databases: Array<{
    name: string;
    r: boolean;
    w: boolean;
    d: boolean;
    a: boolean;
  }> = [];

  let initialized = false;

  // Database selector state
  let showDbSelector = false;
  let availableDatabases: string[] = [];
  let isLoadingDbs = false;
  let isSearchingDbs = false;

  // Initialize databases array from grants object on mount
  onMount(() => {
    initializeDatabases();
    initialized = true;
  });

  function initializeDatabases() {
    if (grants && Object.keys(grants).length > 0) {
      databases = Object.entries(grants).map(([name, perms]) => ({
        name,
        r: perms.r || false,
        w: perms.w || false,
        d: perms.d || false,
        a: perms.a || false,
      }));
    } else {
      databases = [];
    }
  }

  // Sync databases array back to grants object
  function syncGrants() {
    const newGrants: Record<
      string,
      { r: boolean; w: boolean; d: boolean; a: boolean }
    > = {};
    databases.forEach((db) => {
      newGrants[db.name] = {
        r: db.r,
        w: db.w,
        d: db.d,
        a: db.a,
      };
    });
    grants = newGrants;
  }

  // Watch for external changes to grants prop
  $: if (initialized) {
    initializeDatabases();
  }

  async function searchDatabases() {
    isSearchingDbs = true;
    try {
      const searchParam = newDbName.trim()
        ? `search=${encodeURIComponent(newDbName)}&`
        : "";
      const response = await api.apiGet<{
        databases: Array<{ name: string }>;
        total: number;
      }>(`/db?${searchParam}sort=asc&sort_order=1&page=1&page_size=100`);
      availableDatabases = response.databases.map((db) => db.name) || [];
    } catch (error) {
      console.error("Failed to search databases:", error);
      availableDatabases = [];
    } finally {
      isSearchingDbs = false;
    }
  }

  async function loadAvailableDatabases() {
    if (showDbSelector) {
      showDbSelector = false;
      return;
    }

    showDbSelector = true;

    isLoadingDbs = true;
    try {
      // Fetch databases with search filter if input has text
      const searchParam = newDbName.trim()
        ? `search=${encodeURIComponent(newDbName)}&`
        : "";
      const response = await api.apiGet<{
        databases: Array<{ name: string }>;
        total: number;
      }>(`/db?${searchParam}sort=asc&sort_order=1&page=1&page_size=100`);
      availableDatabases = response.databases.map((db) => db.name) || [];
    } catch (error) {
      console.error("Failed to load databases:", error);
      alert(
        "Failed to load databases. You can still enter database names manually."
      );
      showDbSelector = false;
    } finally {
      isLoadingDbs = false;
    }
  }

  function selectDatabase(dbName: string) {
    newDbName = dbName;
    showDbSelector = false;
  }

  function addDatabase() {
    const dbName = newDbName.trim();
    if (!dbName) return;

    // Check if database already exists
    if (databases.some((db) => db.name === dbName)) {
      alert(`Database "${dbName}" already exists`);
      return;
    }

    // Add new database with all permissions disabled
    databases = [
      ...databases,
      { name: dbName, r: false, w: false, d: false, a: false },
    ];
    newDbName = "";
    syncGrants();
  }

  function removeDatabase(dbName: string) {
    databases = databases.filter((db) => db.name !== dbName);
    syncGrants();
  }

  function togglePermission(dbName: string, permission: "r" | "w" | "d" | "a") {
    databases = databases.map((db) => {
      if (db.name === dbName) {
        const newDb = { ...db };

        if (permission === "a" && !allowAdmin) {
          // Don't allow admin permission if not allowed
          return db;
        }

        if (permission === "a") {
          // Admin auto-ticks all others
          const newValue = !db.a;
          newDb.a = newValue;
          if (newValue) {
            newDb.r = true;
            newDb.w = true;
            newDb.d = true;
          }
        } else if (permission === "w" || permission === "d") {
          // Write/Delete auto-tick View
          const newValue = !db[permission];
          newDb[permission] = newValue;
          if (newValue) {
            newDb.r = true;
          }
        } else if (permission === "r") {
          // If unchecking View, uncheck everything
          const newValue = !db.r;
          newDb.r = newValue;
          if (!newValue) {
            newDb.w = false;
            newDb.d = false;
            if (allowAdmin) {
              newDb.a = false;
            }
          }
        }

        return newDb;
      }
      return db;
    });
    syncGrants();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault();
      addDatabase();
    }
  }
</script>

<div class="flex gap-6 h-full">
  <!-- Left: Description (30%) - Only show if description is not undefined -->
  {#if description !== undefined}
    <div class="w-[30%] flex flex-col">
      <div class="label">
        <span class="label-text">
          Description
          <span class="text-error">*</span>
        </span>
      </div>
      <textarea
        bind:value={description}
        placeholder="Describe this permission group"
        class="textarea textarea-bordered w-full flex-1 resize-none"
      ></textarea>
    </div>
  {/if}

  <!-- Right: Database Grants (70% or 100% if no description) -->
  <div
    class="{description !== undefined
      ? 'w-[70%]'
      : 'w-full'} flex flex-col space-y-4"
  >
    <div class="label flex items-center">
      <span class="label-text">{title}</span>
      <div
        class="tooltip tooltip-right"
        data-tip="You can use patterns like 'proj-*' or '*' (super-admin) to match multiple databases."
      >
        <i class="fas fa-info-circle text-info cursor-help"></i>
      </div>
    </div>

    <!-- Add Database Input with Selector -->
    <div class="relative">
      <div class="flex gap-2">
        <div class="form-control w-full">
          <label
            class="input input-bordered input-sm flex items-center gap-2 w-full"
          >
            <input
              type="text"
              placeholder="Enter database name or pattern (e.g., proj-*)"
              class="grow"
              bind:value={newDbName}
              on:keydown={handleKeydown}
              on:input={() => {
                if (showDbSelector) searchDatabases();
              }}
            />

            <button
              type="button"
              class="btn btn-ghost btn-xs btn-circle"
              on:click={() => {
                if (showDbSelector) {
                  searchDatabases();
                } else {
                  loadAvailableDatabases();
                }
              }}
              disabled={isSearchingDbs || isLoadingDbs}
              aria-label="Search databases"
            >
              {#if isSearchingDbs || isLoadingDbs}
                <span class="loading loading-ring loading-xs"></span>
              {:else}
                <i class="fas fa-search text-xs"></i>
              {/if}
            </button>
          </label>
        </div>

        <button
          class="btn btn-primary btn-sm"
          on:click={addDatabase}
          disabled={!newDbName.trim()}
        >
          <i class="fas fa-plus mr-1"></i>
          Add
        </button>
      </div>

      <!-- Database Selector Dropdown -->
      {#if showDbSelector}
        <div
          class="absolute top-full left-0 right-0 mt-2 border border-base-300 rounded-lg p-3 bg-base-100 shadow-lg z-20"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold">Select Database</span>
            <button
              class="btn btn-ghost btn-xs"
              on:click={() => (showDbSelector = false)}
              aria-label="Close database selector"
            >
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="max-h-48 overflow-y-auto space-y-1">
            {#if availableDatabases.length > 0}
              {#each availableDatabases as dbName}
                <button
                  class="btn btn-ghost btn-sm w-full justify-start font-mono text-xs"
                  on:click={() => selectDatabase(dbName)}
                  disabled={databases.some((db) => db.name === dbName)}
                >
                  <i class="fas fa-database mr-2 text-xs"></i>
                  {dbName}
                  {#if databases.some((db) => db.name === dbName)}
                    <span class="ml-auto badge badge-sm">Added</span>
                  {/if}
                </button>
              {/each}
            {:else}
              <div class="text-center text-sm text-base-content/50 py-4">
                {isSearchingDbs
                  ? "Searching..."
                  : newDbName
                    ? "No databases match your search"
                    : "No databases available"}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>

    <!-- Databases Table -->
    <div
      class="h-52 overflow-x-auto overflow-y-auto border border-base-300 rounded-box"
    >
      {#if databases.length > 0}
        <table class="table table-xs w-full">
          <thead class="sticky top-0 bg-primary/40 z-10">
            <tr>
              <th class="w-1/3">Database</th>
              <th class="text-center">View</th>
              <th class="text-center">Edit</th>
              <th class="text-center">Delete</th>
              {#if allowAdmin}
                <th class="text-center">Admin</th>
              {/if}
              <th class="w-16"></th>
            </tr>
          </thead>
          <tbody>
            {#each databases as db (db.name)}
              <tr class="hover">
                <td class="font-mono text-xs font-semibold">{db.name}</td>
                <td class="text-center">
                  <input
                    type="checkbox"
                    class="checkbox checkbox-xs"
                    checked={db.r}
                    on:change={() => togglePermission(db.name, "r")}
                  />
                </td>
                <td class="text-center">
                  <input
                    type="checkbox"
                    class="checkbox checkbox-xs"
                    checked={db.w}
                    on:change={() => togglePermission(db.name, "w")}
                  />
                </td>
                <td class="text-center">
                  <input
                    type="checkbox"
                    class="checkbox checkbox-xs"
                    checked={db.d}
                    on:change={() => togglePermission(db.name, "d")}
                  />
                </td>
                {#if allowAdmin}
                  <td class="text-center">
                    <input
                      type="checkbox"
                      class="checkbox checkbox-xs"
                      checked={db.a}
                      on:change={() => togglePermission(db.name, "a")}
                    />
                  </td>
                {/if}
                <td class="text-center">
                  <button
                    class="btn btn-ghost btn-xs"
                    on:click={() => removeDatabase(db.name)}
                    aria-label="Remove database"
                  >
                    <i class="fas fa-times"></i>
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="flex items-center poppins justify-center h-full">
          <p class="text-xs">Add a database above to configure permissions</p>
        </div>
      {/if}
    </div>
  </div>
</div>
