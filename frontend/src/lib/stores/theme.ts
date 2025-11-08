import { derived, writable } from "svelte/store";

export type ThemeOption = {
  name: string;
  icon: string;
  tooltip: string;
};

export const availableThemes: ThemeOption[] = [
  { name: "light", icon: "fa-sun", tooltip: "Light" },
  { name: "dark", icon: "fa-moon", tooltip: "Dark" },
  { name: "emerald", icon: "fa-leaf", tooltip: "Emerald" },
  { name: "forest", icon: "fa-tree", tooltip: "Forest" },
  { name: "autumn", icon: "fa-cloud-sun", tooltip: "Autumn" },
];

const initialThemeName =
  typeof localStorage !== "undefined" &&
  availableThemes.some((t) => t.name === localStorage.getItem("theme"))
    ? localStorage.getItem("theme")!
    : "light";

export const theme = writable<string>(initialThemeName);

export function setTheme(newTheme: string) {
  if (!availableThemes.some((t) => t.name === newTheme)) return;

  theme.set(newTheme);
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", newTheme);
  }
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("theme", newTheme);
  }
}

// Derived store that automatically calculates the next theme in the sequence.
export const nextTheme = derived(theme, ($theme) => {
  const currentIndex = availableThemes.findIndex((t) => t.name === $theme);
  const nextIndex = (currentIndex + 1) % availableThemes.length;
  return availableThemes[nextIndex];
});


