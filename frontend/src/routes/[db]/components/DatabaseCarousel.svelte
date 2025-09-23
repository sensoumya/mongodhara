<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { fade } from "svelte/transition";

  export let currentIndex: number = 0;

  const slideTitles = ["Collections", "GridFS Buckets"];
  const dispatch = createEventDispatcher<{
    change: { index: number };
  }>();

  function handleCarouselChange(newIndex: number) {
    if (newIndex >= 0 && newIndex < slideTitles.length) {
      currentIndex = newIndex;
      dispatch("change", { index: newIndex });
    }
  }
</script>

<div>
  <div class="carousel w-full relative">
    {#key currentIndex}
      {#if currentIndex === 0}
        <div
          class="carousel-item w-full justify-center"
          in:fade={{ duration: 400, delay: 200 }}
          out:fade={{ duration: 200 }}
        >
          <h1 class="text-3xl poppins mb-3 mt-3 text-center">
            <i class="fa-solid fa-layer-group text-primary"></i>
            {slideTitles[0]}
          </h1>
        </div>
      {:else if currentIndex === 1}
        <div
          class="carousel-item w-full justify-center"
          in:fade={{ duration: 400, delay: 200 }}
          out:fade={{ duration: 200 }}
        >
          <h1 class="text-3xl poppins mb-3 mt-3 text-center">
            <i class="fa-solid fa-bucket text-primary"></i>
            {slideTitles[1]}
          </h1>
        </div>
      {/if}
    {/key}

    <!-- Carousel navigation buttons -->
    <div
      class="absolute flex justify-between transform -translate-y-1/2 left-0 right-0 top-1/2 w-full px-4"
    >
      <!-- Previous Button -->
      <button
        class="btn btn-ghost flex items-center gap-2 text-2xl text-primary/60 hover:bg-transparent hover:text-primary border-transparent hover:border-transparent focus:border-transparent"
        on:click={() => handleCarouselChange(currentIndex - 1)}
        aria-label="Previous"
        disabled={currentIndex === 0}
        style="min-width: 120px; outline: none; box-shadow: none;"
      >
        {#if currentIndex > 0}
          <i class="fa-solid fa-angles-left hover-beat-fade"></i>
        {/if}
        <span
          style="opacity: {currentIndex > 0
            ? 1
            : 0}; transition: opacity 0.2s; min-width: 90px; display: inline-block;"
        >
          {currentIndex > 0 ? slideTitles[currentIndex - 1] : ""}
        </span>
      </button>

      <!-- Next Button -->
      <button
        class="btn btn-ghost flex items-center gap-2 text-2xl text-primary/60 justify-end hover:bg-transparent hover:text-primary border-transparent hover:border-transparent focus:border-transparent"
        on:click={() => handleCarouselChange(currentIndex + 1)}
        aria-label="Next"
        disabled={currentIndex === slideTitles.length - 1}
        style="min-width: 120px; outline: none; box-shadow: none;"
      >
        <span
          style="opacity: {currentIndex < slideTitles.length - 1
            ? 1
            : 0}; transition: opacity 0.2s; min-width: 90px; display: inline-block;"
        >
          {currentIndex < slideTitles.length - 1
            ? slideTitles[currentIndex + 1]
            : ""}
        </span>
        {#if currentIndex < slideTitles.length - 1}
          <i class="fa-solid fa-angles-right hover-beat-fade"></i>
        {/if}
      </button>
    </div>
  </div>
</div>

<style>
  .poppins {
    font-family: "Poppins", sans-serif;
  }

  /* FontAwesome beat-fade animation on hover */
  .hover-beat-fade {
    transition: all 0.2s ease;
  }

  button:hover .hover-beat-fade {
    animation: fa-beat-fade 1s ease-in-out infinite;
  }

  /* FontAwesome keyframes for beat-fade animation */
  @keyframes fa-beat-fade {
    0%,
    100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.4;
      transform: scale(1.125);
    }
  }
</style>
