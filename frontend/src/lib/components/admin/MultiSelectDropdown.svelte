<script lang="ts">
  export let selected: string[] = [];
  export let options: Array<{
    value: string;
    label: string;
    description?: string;
  }> = [];
  export let placeholder: string = "Select items...";

  let isOpen = false;
  let searchTerm = "";

  $: filteredOptions = options.filter(
    (opt) =>
      opt.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      opt.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function toggleOption(value: string) {
    if (selected.includes(value)) {
      selected = selected.filter((v) => v !== value);
    } else {
      selected = [...selected, value];
    }
  }

  function removeSelected(value: string, event: Event) {
    event.stopPropagation();
    selected = selected.filter((v) => v !== value);
  }

  function getLabel(value: string): string {
    return options.find((opt) => opt.value === value)?.label || value;
  }

  let containerElement: HTMLDivElement;

  function handleClickOutside(event: MouseEvent) {
    if (containerElement && !containerElement.contains(event.target as Node)) {
      isOpen = false;
      searchTerm = "";
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && isOpen) {
      isOpen = false;
      searchTerm = "";
    }
  }
</script>

<svelte:window
  on:keydown={handleKeydown}
  on:click|capture={isOpen ? handleClickOutside : null}
/>

<div class="multiselect-container relative" bind:this={containerElement}>
  <div
    class="input input-bordered w-full min-h-[2.5rem] h-[2.5rem] max-h-[9rem] p-2 flex flex-wrap gap-2 items-center cursor-pointer overflow-y-auto"
    on:click|stopPropagation={() => (isOpen = !isOpen)}
    on:keydown={(e) => e.key === "Enter" && (isOpen = !isOpen)}
    role="button"
    tabindex="0"
  >
    {#if selected.length === 0}
      <span class="text-base-content/50">{placeholder}</span>
    {:else}
      {#each selected as value}
        <div class="badge badge-accent gap-2 py-3 px-3">
          <span>{getLabel(value)}</span>
          <button
            class="text-xs hover:text-error"
            type="button"
            on:click={(e) => removeSelected(value, e)}
          >
            ✕
          </button>
        </div>
      {/each}
    {/if}
    <div class="flex-1 min-w-5"></div>
    <i class="fas fa-chevron-down text-sm text-base-content/50"></i>
  </div>

  {#if isOpen}
    <div
      class="absolute z-50 w-full mt-2 bg-base-100 border border-base-300 rounded-lg shadow-lg max-h-80 overflow-hidden flex flex-col"
    >
      <div class="p-2 border-b border-base-300">
        <input
          type="text"
          bind:value={searchTerm}
          placeholder="Search..."
          class="input input-sm input-bordered w-full"
          on:click|stopPropagation
        />
      </div>
      <div class="overflow-y-auto">
        {#if filteredOptions.length === 0}
          <div class="p-3 text-center text-sm text-base-content/50">
            No options found
          </div>
        {:else}
          {#each filteredOptions as option}
            <div
              class="p-2 hover:bg-base-200 cursor-pointer border-b border-base-300 last:border-b-0"
              on:click|stopPropagation={() => toggleOption(option.value)}
              on:keydown={(e) =>
                e.key === "Enter" && toggleOption(option.value)}
              role="option"
              aria-selected={selected.includes(option.value)}
              tabindex="0"
            >
              <div class="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={selected.includes(option.value)}
                  class="checkbox checkbox-sm checkbox-accent mt-0.5"
                  on:click|stopPropagation={() => toggleOption(option.value)}
                />
                <div class="flex-1">
                  <div class="text-sm font-medium">{option.label}</div>
                  {#if option.description}
                    <div class="text-xs text-base-content/60 mt-0.5">
                      {option.description}
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>
