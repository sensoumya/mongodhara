<script lang="ts">
  import { createEventDispatcher } from "svelte";

  export let currentIndex: number = 0;

  const tabs = [
    { title: "Collections", icon: "fa-solid fa-layer-group" },
    { title: "GridFS Buckets", icon: "fa-solid fa-bucket" },
  ];

  const dispatch = createEventDispatcher<{
    change: { index: number };
  }>();

  function handleTabChange(newIndex: number) {
    if (newIndex >= 0 && newIndex < tabs.length) {
      currentIndex = newIndex;
      dispatch("change", { index: newIndex });
    }
  }
</script>

<div class="w-full">
  <h1
    class="text-2xl poppins mb-8 text-center flex items-center justify-center gap-4"
  >
    {#each tabs as tab, index}
      <button
        class="flex items-center gap-2 transition-all duration-200 {currentIndex ===
        index
          ? 'cursor-default'
          : 'text-base opacity-30 hover:opacity-60 cursor-pointer'}"
        on:click={() => currentIndex !== index && handleTabChange(index)}
        aria-selected={currentIndex === index}
        disabled={currentIndex === index}
      >
        <i class="{tab.icon} text-primary"></i>
        <span>{tab.title}</span>
      </button>
      {#if index < tabs.length - 1}
        <div class="divider divider-horizontal mx-0"></div>
      {/if}
    {/each}
  </h1>
</div>

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }
</style>
