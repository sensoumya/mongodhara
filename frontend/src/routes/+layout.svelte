<script lang="ts">
  import { base, resolve } from "$app/paths";
  import { env } from "$env/dynamic/public";
  import AdminOverlay from "$lib/components/AdminOverlay.svelte";
  import ErrOverlay from "$lib/components/ErrorOverlay.svelte";
  import NotificationList from "$lib/components/NotificationList.svelte";
  import * as api from "$lib/stores/api";
  import { nextTheme, setTheme, theme } from "$lib/stores/theme";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import "../app.css";

  const authzEnabled = env.PUBLIC_AUTHZ_ENABLED === "true";

  let isReady = false;
  let showContent = false;

  let showAdminOverlay = false;
  let userRole: string | null = null;
  let userEmail: string | null = null;

  onMount(async () => {
    if (!localStorage.getItem("theme")) {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches;
      setTheme(prefersDark ? "dark" : "light");
    }

    // Fetch user role from API only when authz is enabled
    if (authzEnabled) {
      try {
        const response = (await api.apiPost("/permissions/check", {})) as {
          role: string;
          user_email: string;
        };
        userRole = response.role || null;
        userEmail = response.user_email || null;
        if (userRole) sessionStorage.setItem("userRole", userRole);
        if (userEmail) sessionStorage.setItem("userEmail", userEmail);
      } catch (error) {
        console.error("Failed to fetch user role:", error);
        userRole = sessionStorage.getItem("userRole") || "user";
        userEmail = sessionStorage.getItem("userEmail") || null;
      }
    }

    // Mark as ready after all checks are complete
    isReady = true;
    // Delay showing content to allow fade out to complete
    setTimeout(() => {
      showContent = true;
    }, 300);
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
    const pdfUrl = `${base}/tutorial.pdf`;
    window.open(pdfUrl, "_blank");
  }

  // Handle cockpit button click
  function handleCockpitClick() {
    showAdminOverlay = true;
  }
</script>

{#if !isReady || !showContent}
  <!-- Loading state to prevent flicker -->
  <div
    class="flex flex-col min-h-screen bg-base-100 text-base-content items-center justify-center"
    data-theme={$theme}
    out:fade={{ duration: 300 }}
  >
    <div class="text-4xl font-poppins flex items-center animate-pulse">
      <span class="text-secondary/70">mongo</span>
      <span
        class="text-5xl font-bold font-roboto bg-primary text-primary-content px-3 py-2 rounded-lg inline-flex items-center ml-2"
        >Dhārā<span style="display:inline-block; transform: skewX(-10deg);"
          >!</span
        >
      </span>
    </div>
  </div>
{/if}

{#if showContent}
  <div
    class="flex flex-col min-h-screen bg-base-100 text-base-content selection:bg-primary/30"
    data-theme={$theme}
    in:fade={{ duration: 400, delay: 100 }}
  >
    <!-- Global error overlay -->
    <ErrOverlay />

    <!-- Admin overlay -->
    <AdminOverlay bind:show={showAdminOverlay} />

    <header class="bg-base-100 top-0 z-50 w-full">
      <div class="flex items-center justify-between px-4 py-2">
        <a
          href={resolve("/")}
          class="text-xl font-poppins flex items-center"
          on:click={handleLogoClick}
        >
          <span class="text-secondary/70">mongo</span>
          <span
            class="text-3xl font-bold font-roboto bg-primary text-primary-content px-2 py-1 rounded-lg inline-flex items-center ml-1"
            >Dhārā<span style="display:inline-block; transform: skewX(-10deg);"
              >!</span
            >
          </span>
          <span class="text-xs text-base-content/60 ml-3 self-end relative">
            v2.2
          </span>
        </a>

        <div class="flex items-center gap-4">
          {#if authzEnabled && userEmail}
            <div
              class="flex items-center gap-2 poppins text-sm text-base-content/70"
            >
              <!-- <i class="fa-solid fa-user"></i> -->
              <span class="hidden text-xs sm:inline">{userEmail}</span>
              {#if userRole === "admin"}
                <span class="badge badge-neutral badge-xs">ADMIN</span>
              {:else}
                <span class="badge badge-neutral badge-xs">USER</span>
              {/if}
            </div>
            <div class="divider divider-horizontal mx-0"></div>
          {/if}
          <button
            class="hover:text-secondary transition-colors cursor-pointer active:scale-95 min-w-24 text-left"
            on:click={toggleTheme}
            aria-label="Toggle Theme"
          >
            <i class="fa-solid {$nextTheme.icon}"></i>
            <span class="hidden text-sm md:inline">Go {$nextTheme.tooltip}</span
            >
          </button>
          {#if authzEnabled && userRole === "admin"}
            <button
              on:click={handleCockpitClick}
              class="{showAdminOverlay
                ? 'text-secondary'
                : ''} hover:text-secondary transition-colors cursor-pointer active:scale-95"
              aria-label="Open Admin Cockpit"
            >
              <i class="fa-solid fa-gear"></i>
              <span class="hidden text-sm md:inline">Control Hub</span>
            </button>
          {/if}
        </div>
      </div>
    </header>
    <NotificationList />
    <main class="flex-1 px-4 max-w-7xl mx-auto w-full">
      <slot />
    </main>
  </div>
{/if}
