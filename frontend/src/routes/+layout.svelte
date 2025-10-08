<script lang="ts">
  import { base, resolve } from "$app/paths";
  import ErrOverlay from "$lib/components/ErrorOverlay.svelte";
  import NotificationList from "$lib/components/NotificationList.svelte";
  import { nextTheme, setTheme, theme } from "$lib/stores/theme";
  import { onMount } from "svelte";
  import "../app.css";

  onMount(() => {
    if (!localStorage.getItem("theme")) {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches;
      setTheme(prefersDark ? "dark" : "light");
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

  // Handle tutorial opening in new tab
  function handleTutorialOpen() {
    const pdfUrl = ${base}/tutorial.pdf;
    window.open(pdfUrl, "_blank");
  }
</script>

<div
  class="min-h-screen bg-base-100 text-base-content selection:bg-primary/30"
  data-theme={$theme}
>
  <!-- Global error overlay -->
  <ErrOverlay />

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
          <span class="text-sm text-base-content/60 ml-3 self-end relative">
            v2.1
          </span>
        </a>

        <div class="flex items-center gap-2">
          <button
            on:click={handleTutorialOpen}
            class="btn btn-ghost btn-sm tooltip tooltip-bottom"
            data-tip="Open Tutorial Guide"
            aria-label="Open Tutorial Guide"
          >
            <i class="fa-regular fa-circle-play text-xl"></i>
          </button>

          <button
            class="btn btn-ghost btn-sm tooltip tooltip-bottom"
            on:click={toggleTheme}
            data-tip={$nextTheme.tooltip}
            aria-label="Toggle Theme"
          >
            <i class="fa-solid {$nextTheme.icon} text-xl"></i>
          </button>
        </div>
      </div>
    </header>

    <NotificationList />

    <main class="p-4 max-w-7xl mx-auto">
      <slot />
    </main>
  </div>
</div>