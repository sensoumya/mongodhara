<script lang="ts">
  export let tags: string[] = [];
  export let placeholder: string = "Add item...";
  export let validate: (value: string) => boolean = () => true;
  export let errorMessage: string = "Invalid input";

  let inputValue: string = "";
  let showError: boolean = false;

  function addTag() {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    if (!validate(trimmed)) {
      showError = true;
      return;
    }

    if (!tags.includes(trimmed)) {
      tags = [...tags, trimmed];
    }

    inputValue = "";
    showError = false;
  }

  function removeTag(index: number) {
    tags = tags.filter((_, i) => i !== index);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault();
      addTag();
    } else if (event.key === "Backspace" && !inputValue && tags.length > 0) {
      removeTag(tags.length - 1);
    } else {
      showError = false;
    }
  }
</script>

<div class="space-y-2">
  <div
    class="input input-bordered w-full min-h-[2.5rem] h-[2.5rem] max-h-[9rem] p-2 flex flex-wrap gap-2 items-center overflow-y-auto"
  >
    {#each tags as tag, index}
      <div
        class="badge badge-accent gap-2 py-2 px-2 cursor-pointer text-sm"
        on:click={() => removeTag(index)}
        on:keydown={(e) => e.key === "Enter" && removeTag(index)}
        role="button"
        tabindex="0"
      >
        <span>{tag}</span>
        <button class="text-xs" type="button">✕</button>
      </div>
    {/each}
    <input
      type="text"
      bind:value={inputValue}
      on:keydown={handleKeydown}
      on:blur={addTag}
      {placeholder}
      class="flex-1 min-w-32 text-sm outline-none bg-transparent"
    />
  </div>
  {#if showError}
    <p class="text-error text-sm">{errorMessage}</p>
  {/if}
</div>
