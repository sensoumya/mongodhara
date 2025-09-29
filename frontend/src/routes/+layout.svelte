<script lang="ts">
  import { resolve } from "$app/paths";
  import AuthExpiredOverlay from "$lib/components/AuthExpiredOverlay.svelte";
  import NotificationList from "$lib/components/NotificationList.svelte";
  import { nextTheme, setTheme, theme } from "$lib/stores/theme";
  import { onMount } from "svelte";
  import "../app.css";

  // Use the derived store to get the next theme's data automatically.
  // No need for a separate reactive block.
  // The 'theme' store is still imported to keep the DOM element updated.

  // Initialize theme on mount.
  onMount(() => {
    if (!localStorage.getItem("theme")) {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches;
      setTheme(prefersDark ? "forest" : "emerald");
    }
  });

  // Toggle logic: sets the next theme's name.
  function toggleTheme() {
    setTheme($nextTheme.name);
  }

  // Force a full page reload for a hard navigation.
  function handleLogoClick(event: MouseEvent) {
    event.preventDefault();
    window.location.href = resolve("/");
  }
</script>

<div
  class="min-h-screen bg-base-100 text-base-content selection:bg-primary/30"
  data-theme={$theme}
>
  <!-- Global error overlay -->
  <AuthExpiredOverlay />

  <div class="relative min-h-screen">
    <header class="bg-base-200 shadow-md sticky top-0 z-50">
      <div
        class="max-w-7xl mx-auto flex items-center justify-between px-4 py-2"
      >
        <a
          href={resolve("/")}
          class="text-2xl font-poppins flex items-center"
          on:click={handleLogoClick}
        >
          <span class="text-secondary/70">mongo</span>
          <span
            class="text-4xl font-bold font-roboto bg-primary text-primary-content px-2 py-1 rounded-lg inline-flex items-center ml-1"
            >Dhārā<span style="display:inline-block; transform: skewX(-10deg);"
              >!</span
            >
          </span>
        </a>

        <button
          class="btn btn-ghost btn-sm tooltip tooltip-bottom"
          on:click={toggleTheme}
          data-tip={$nextTheme.tooltip}
        >
          <i class="fa-solid {$nextTheme.icon} text-xl"></i>
        </button>
      </div>
    </header>

    <NotificationList />

    <main class="p-4 max-w-7xl mx-auto">
      <slot />
    </main>
  </div>
</div>
