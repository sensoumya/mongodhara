import { derived, writable } from "svelte/store";

export type ThemeOption = {
  name: string;
  icon: string;
};

export const availableThemes: ThemeOption[] = [
  { name: "light", icon: "fa-sun", tooltip: "Switch to Light Theme" },
  { name: "dark", icon: "fa-moon", tooltip: "Switch to Dark Theme" },
  { name: "emerald", icon: "fa-leaf", tooltip: "Switch to Emerald Theme" },
  { name: "forest", icon: "fa-tree", tooltip: "Switch to Forest Theme" },
  { name: "autumn", icon: "fa-cloud-sun", tooltip: "Switch to Autumn Theme" },
];

const initialThemeName =
  typeof localStorage !== "undefined" &&
  availableThemes.some((t) => t.name === localStorage.getItem("theme"))
    ? localStorage.getItem("theme")!
    : "emerald";

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


