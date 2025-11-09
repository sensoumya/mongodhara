<script lang="ts">
  import {
    mongoOperators,
    type MongoOperator,
  } from "$lib/utils/mongoOperators";
  import {
    beautifyJSON,
    calculateDropdownPosition,
    detectTrigger,
    filterItems,
    getCursorPosition,
    insertTextAtCursor,
    validateJSON,
    type TriggerInfo,
  } from "$lib/utils/queryAutocomplete";
  import {
    refreshDynamicValues,
    valueHelpers,
    type ValueHelper,
  } from "$lib/utils/valueHelpers";
  import { createEventDispatcher, onMount } from "svelte";
  import { fade } from "svelte/transition";

  // Props
  export let value: string = "";
  export let placeholder: string = "JSON query...";
  export let availableFields: string[] = [];
  export let disabled: boolean = false;
  export let submitLabel: string = "Search";

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // UI state
  let isQueryMaximized = false;
  let validationError: string | null = null;

  // Autocomplete state
  let showAutocomplete = false;
  let autocompleteOptions: (MongoOperator | ValueHelper | string)[] = [];
  let autocompleteType: "@" | "/" | "#" | null = null;
  let selectedIndex = 0;
  let triggerInfo: TriggerInfo = { type: null, position: 0, searchText: "" };
  let dropdownPosition = { top: 0, left: 0 };

  // Element references
  let inputElement: HTMLInputElement;
  let textareaElement: HTMLTextAreaElement;

  // Reactive validation
  $: {
    if (isQueryMaximized && value.trim() !== "") {
      const validation = validateJSON(value);
      validationError = validation.valid ? null : validation.error || null;
    } else {
      validationError = null;
    }
  }

  /**
   * Handle paste event - auto-beautify JSON if valid
   */
  function handlePaste(event: ClipboardEvent) {
    const pastedText = event.clipboardData?.getData("text");
    if (!pastedText) return;

    // Try to parse and beautify the pasted JSON
    try {
      const parsed = JSON.parse(pastedText);
      const beautified = JSON.stringify(parsed, null, 2);

      // Prevent default paste and insert beautified version
      event.preventDefault();
      const target = event.target as HTMLTextAreaElement;
      const start = target.selectionStart || 0;
      const end = target.selectionEnd || 0;

      value = value.substring(0, start) + beautified + value.substring(end);

      // Set cursor position after inserted text
      setTimeout(() => {
        const newPosition = start + beautified.length;
        target.setSelectionRange(newPosition, newPosition);
      }, 0);
    } catch {
      // If not valid JSON, let default paste behavior happen
    }
  }

  /**
   * Handle input changes and check for autocomplete triggers
   */
  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement;
    value = target.value;

    const cursorPos = getCursorPosition(target);
    triggerInfo = detectTrigger(value, cursorPos.start);

    if (triggerInfo.type === "@") {
      // Show MongoDB operators
      const filtered = filterItems(
        mongoOperators,
        triggerInfo.searchText,
        (op) => op.operator + " " + op.description
      );
      autocompleteOptions = filtered;
      autocompleteType = "@";
      showAutocomplete = filtered.length > 0;
      selectedIndex = 0;
      updateDropdownPosition(target);
    } else if (triggerInfo.type === "/") {
      // Show available fields
      const filtered = filterItems(
        availableFields,
        triggerInfo.searchText,
        (field) => field
      );
      autocompleteOptions = filtered;
      autocompleteType = "/";
      showAutocomplete = filtered.length > 0;
      selectedIndex = 0;
      updateDropdownPosition(target);
    } else if (triggerInfo.type === "#") {
      // Show value helpers (refresh dynamic DateTime values first)
      refreshDynamicValues();
      const filtered = filterItems(
        valueHelpers,
        triggerInfo.searchText,
        (helper) => helper.key + " " + helper.description
      );
      autocompleteOptions = filtered;
      autocompleteType = "#";
      showAutocomplete = filtered.length > 0;
      selectedIndex = 0;
      updateDropdownPosition(target);
    } else {
      closeAutocomplete();
    }

    dispatch("change", { value });
  }

  /**
   * Handle keyboard navigation for autocomplete
   */
  function handleKeydown(event: KeyboardEvent) {
    // Handle auto-closing brackets and quotes
    if (!showAutocomplete) {
      const target = event.target as HTMLTextAreaElement | HTMLInputElement;
      const { selectionStart, selectionEnd } = target;

      const closingPairs: Record<string, string> = {
        "{": "}",
        "[": "]",
        '"': '"',
        "'": "'",
      };

      if (closingPairs[event.key]) {
        event.preventDefault();
        const closingChar = closingPairs[event.key];

        if (selectionStart === selectionEnd) {
          // No selection - insert pair and place cursor between
          const newValue =
            value.substring(0, selectionStart) +
            event.key +
            closingChar +
            value.substring(selectionEnd);
          value = newValue;

          // Position cursor between the pair
          setTimeout(() => {
            target.setSelectionRange(selectionStart + 1, selectionStart + 1);
          }, 0);
        } else {
          // Has selection - wrap selection with pair
          const selectedText = value.substring(selectionStart, selectionEnd);
          const newValue =
            value.substring(0, selectionStart) +
            event.key +
            selectedText +
            closingChar +
            value.substring(selectionEnd);
          value = newValue;

          // Select the wrapped text (excluding the wrapper characters)
          setTimeout(() => {
            target.setSelectionRange(selectionStart + 1, selectionEnd + 1);
          }, 0);
        }
        return;
      }
    }

    if (!showAutocomplete) return;

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        selectedIndex = Math.min(
          selectedIndex + 1,
          autocompleteOptions.length - 1
        );
        scrollToSelected();
        break;
      case "ArrowUp":
        event.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        scrollToSelected();
        break;
      case "Enter":
        if (showAutocomplete) {
          event.preventDefault();
          selectSuggestion(autocompleteOptions[selectedIndex]);
        }
        break;
      case "Escape":
        event.preventDefault();
        closeAutocomplete();
        break;
      case "Tab":
        if (showAutocomplete) {
          event.preventDefault();
          selectSuggestion(autocompleteOptions[selectedIndex]);
        }
        break;
    }
  }

  /**
   * Select an autocomplete suggestion
   */
  function selectSuggestion(suggestion: MongoOperator | ValueHelper | string) {
    const element = textareaElement || inputElement;
    if (!element) return;

    if (
      autocompleteType === "@" &&
      typeof suggestion === "object" &&
      "operator" in suggestion
    ) {
      // Check if we're already inside braces by looking at context before trigger
      const textBeforeTrigger = value.substring(0, triggerInfo.position);
      const isInsideBraces = isWithinBraces(textBeforeTrigger);

      let templateToInsert = suggestion.template;
      let cursorOffset = suggestion.cursorOffset;
      let selectLength = suggestion.selectLength;

      // If already inside braces, strip outer braces from template
      if (isInsideBraces) {
        // Remove outer { } from template: { "field": { "$op": "value" } } -> "field": { "$op": "value" }
        const trimmed = suggestion.template.trim();
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
          templateToInsert = trimmed.substring(1, trimmed.length - 1).trim();
          // Adjust cursor offset - we removed "{ " (2 chars: brace and space)
          if (cursorOffset !== undefined) {
            cursorOffset = Math.max(0, cursorOffset - 2);
          }
        }

        // Smart comma insertion: check if we need a comma before the new field
        if (
          needsCommaBeforeInsertion(textBeforeTrigger, triggerInfo.position)
        ) {
          templateToInsert = ", " + templateToInsert;
          // Adjust cursor offset for the added comma and space
          if (cursorOffset !== undefined) {
            cursorOffset = cursorOffset + 2;
          }
        }
      }

      // Insert MongoDB operator template with text selection
      insertTextAtCursor(
        element,
        templateToInsert,
        triggerInfo.position,
        triggerInfo.searchText.length,
        cursorOffset,
        selectLength
      );
    } else if (
      autocompleteType === "#" &&
      typeof suggestion === "object" &&
      "key" in suggestion
    ) {
      // Insert value helper template with text selection
      insertTextAtCursor(
        element,
        suggestion.template,
        triggerInfo.position,
        triggerInfo.searchText.length,
        suggestion.cursorOffset,
        suggestion.selectLength
      );
    } else if (autocompleteType === "/" && typeof suggestion === "string") {
      // Insert field name in quotes
      const fieldText = `"${suggestion}"`;
      insertTextAtCursor(
        element,
        fieldText,
        triggerInfo.position,
        triggerInfo.searchText.length,
        fieldText.length
      );
    }

    closeAutocomplete();
  }

  /**
   * Check if cursor position is within braces by counting open/close braces
   */
  function isWithinBraces(textBeforeCursor: string): boolean {
    let braceCount = 0;
    for (const char of textBeforeCursor) {
      if (char === "{") braceCount++;
      if (char === "}") braceCount--;
    }
    return braceCount > 0;
  }

  /**
   * Check if we need a comma before inserting new content
   * Returns true if the last non-whitespace character before trigger is a closing brace, quote, or value
   */
  function needsCommaBeforeInsertion(
    textBeforeTrigger: string,
    triggerPosition: number
  ): boolean {
    // Look backwards from trigger position, skipping the @ and any whitespace
    let pos = triggerPosition - 1;
    while (pos >= 0 && /\s/.test(textBeforeTrigger[pos])) {
      pos--;
    }

    if (pos < 0) return false;

    const lastChar = textBeforeTrigger[pos];
    // Need comma if previous content ends with }, ], ", ', digit, true, false, null
    return (
      /[}\]"'0-9]/.test(lastChar) ||
      textBeforeTrigger
        .substring(Math.max(0, pos - 4), pos + 1)
        .match(/(true|false|null)$/)
    );
  }

  /**
   * Update dropdown position based on element
   */
  function updateDropdownPosition(
    element: HTMLInputElement | HTMLTextAreaElement
  ) {
    dropdownPosition = calculateDropdownPosition(element, triggerInfo.position);
  }

  /**
   * Close autocomplete dropdown
   */
  function closeAutocomplete() {
    showAutocomplete = false;
    autocompleteOptions = [];
    autocompleteType = null;
    selectedIndex = 0;
  }

  /**
   * Scroll to keep selected item visible in dropdown
   */
  function scrollToSelected() {
    requestAnimationFrame(() => {
      const dropdown = document.querySelector(".autocomplete-dropdown");
      const selectedItem = dropdown?.querySelector(".suggestion-item.selected");
      if (selectedItem && dropdown) {
        selectedItem.scrollIntoView({ block: "nearest" });
      }
    });
  }

  /**
   * Beautify JSON with proper indentation
   */
  function handleBeautify() {
    if (!validationError && value.trim() !== "") {
      value = beautifyJSON(value);
      dispatch("change", { value });
    }
  }

  /**
   * Copy query to clipboard
   */
  async function handleCopy() {
    if (!value || validationError) return;

    try {
      // Beautify before copying
      const beautified = beautifyJSON(value);
      await navigator.clipboard.writeText(beautified);

      // Could add a visual feedback here (e.g., change icon temporarily)
      const button = document.querySelector(
        '[aria-label="Copy query to clipboard"]'
      );
      if (button) {
        const icon = button.querySelector("i");
        if (icon) {
          icon.className = "fas fa-check";
          setTimeout(() => {
            icon.className = "fas fa-copy";
          }, 2000);
        }
      }
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }

  /**
   * Clear the query
   */
  function handleClear() {
    value = "";
    closeAutocomplete();
    dispatch("change", { value });
    dispatch("submit", { query: value });
  }

  /**
   * Submit the query
   */
  function handleSubmit() {
    if (validationError) return;
    dispatch("submit", { query: value });
  }

  /**
   * Handle click outside to close autocomplete
   */
  function handleClickOutside(event: MouseEvent) {
    if (showAutocomplete) {
      const dropdown = document.querySelector(".autocomplete-dropdown");
      if (dropdown && !dropdown.contains(event.target as Node)) {
        closeAutocomplete();
      }
    }
  }

  onMount(() => {
    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  });
</script>

<form
  on:submit|preventDefault={handleSubmit}
  class="flex w-80 flex-shrink-0 query-container relative"
>
  <!-- Collapsed state -->
  <label
    class="input input-ghost input-sm flex items-center gap-2 w-full focus-within:outline-none"
    class:opacity-0={isQueryMaximized}
    class:pointer-events-none={isQueryMaximized}
  >
    <input
      bind:this={inputElement}
      type="text"
      class="text-base outline-none"
      bind:value
      on:input={handleInput}
      on:keydown={handleKeydown}
      placeholder="JSON query..."
    />
    <div class="flex items-center gap-0.5">
      <div class="w-8">
        {#if value}
          <button
            type="button"
            on:click={handleClear}
            class="btn btn-sm btn-ghost btn-circle"
            aria-label="Clear query"
            {disabled}
            in:fade={{ duration: 150 }}
            out:fade={{ duration: 150 }}
          >
            <i class="fas fa-times"></i>
          </button>
        {/if}
      </div>
      <button
        type="button"
        on:click={() => (isQueryMaximized = true)}
        class="btn btn-sm btn-ghost btn-circle"
        aria-label="Expand query input"
      >
        <i class="fas fa-expand"></i>
      </button>
      <button
        type="submit"
        class="btn btn-sm btn-ghost btn-circle"
        aria-label={value ? submitLabel : "Reload"}
        {disabled}
      >
        <i class="fas {value ? 'fa-search' : 'fa-rotate-right'}"></i>
      </button>
    </div>
  </label>

  <!-- Expanded state -->
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="query-expanded-overlay absolute right-0 top-0 bg-base-100 rounded-lg shadow-xl z-50 overflow-hidden"
    class:collapsed={!isQueryMaximized}
    class:expanded={isQueryMaximized}
    on:click|stopPropagation
  >
    <div class="flex flex-col">
      <!-- Button panel at top -->
      <div
        class="flex justify-end items-center gap-2 p-1 bg-base-100 rounded-t-lg pr-3"
      >
        <div class="flex items-center gap-2">
          {#if value}
            <button
              type="button"
              on:click={handleClear}
              class="btn btn-sm btn-base-100 btn-circle"
              aria-label="Clear query"
              {disabled}
              in:fade={{ duration: 150 }}
              out:fade={{ duration: 150 }}
            >
              <i class="fas fa-times"></i>
            </button>
          {/if}
          <button
            type="button"
            on:click={handleBeautify}
            class="btn btn-sm btn-base-100 btn-circle"
            disabled={!!validationError}
            aria-label="Beautify JSON"
          >
            <i class="fas fa-wand-magic-sparkles"></i>
          </button>

          <button
            type="button"
            on:click={handleCopy}
            class="btn btn-sm btn-base-100 btn-circle"
            disabled={!value || !!validationError}
            aria-label="Copy query to clipboard"
            title="Copy to clipboard"
          >
            <i class="fas fa-copy"></i>
          </button>

          <button
            type="button"
            on:click={() => (isQueryMaximized = false)}
            class="btn btn-sm btn-base-100 btn-circle"
            aria-label="Compress query input"
          >
            <i class="fas fa-compress"></i>
          </button>

          <button
            type="submit"
            class="btn btn-sm btn-base-100 btn-circle"
            disabled={!!validationError || disabled}
            aria-label={value ? submitLabel : "Reload"}
          >
            <i class="fas {value ? 'fa-search' : 'fa-rotate-right'}"></i>
          </button>
        </div>
      </div>

      <!-- Textarea container -->
      <div class="p-1">
        <textarea
          bind:this={textareaElement}
          bind:value
          on:input={handleInput}
          on:keydown={handleKeydown}
          on:paste={handlePaste}
          class="textarea w-full h-96 font-mono text-sm resize-none bg-base-200 border-none focus:outline-none"
          placeholder="JSON query...

@  →  MongoDB operators
/  →  Field names
#  →  Common values"
        ></textarea>
        {#if validationError}
          <div class="text-sm text-error mt-2">
            Error: {validationError}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Backdrop for click-outside-to-close -->
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-40 bg-transparent transition-opacity duration-300 ease-in-out"
    class:opacity-0={!isQueryMaximized}
    class:opacity-100={isQueryMaximized}
    class:pointer-events-none={!isQueryMaximized}
    on:click={() => (isQueryMaximized = false)}
  ></div>

  <!-- Autocomplete dropdown -->
  {#if showAutocomplete}
    <div
      class="autocomplete-dropdown fixed bg-base-100 rounded-lg shadow-xl border border-base-300 z-[60] max-h-80 overflow-y-auto"
      style="top: {dropdownPosition.top}px; left: {dropdownPosition.left}px; min-width: 400px; max-width: 600px;"
      in:fade={{ duration: 150 }}
    >
      {#each autocompleteOptions as suggestion, index}
        <button
          type="button"
          class="suggestion-item w-full text-left px-4 py-2 hover:bg-base-200 transition-colors flex items-start gap-3"
          class:selected={index === selectedIndex}
          class:bg-base-200={index === selectedIndex}
          on:click={() => selectSuggestion(suggestion)}
        >
          {#if autocompleteType === "@" && typeof suggestion === "object" && "operator" in suggestion}
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <code class="text-primary font-semibold"
                  >{suggestion.operator}</code
                >
                <span class="badge badge-xs badge-ghost"
                  >{suggestion.category}</span
                >
              </div>
              <div class="text-xs text-base-content/70 mt-1">
                {suggestion.description}
              </div>
            </div>
          {:else if autocompleteType === "#" && typeof suggestion === "object" && "key" in suggestion}
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <code class="text-accent font-semibold">{suggestion.key}</code>
                <span
                  class="badge badge-xs"
                  class:badge-info={suggestion.category === "DateTime"}
                  class:badge-success={suggestion.category === "Common"}
                  class:badge-warning={suggestion.category === "Expandable"}
                  class:badge-neutral={suggestion.category === "Identifier" ||
                    suggestion.category === "Numeric" ||
                    suggestion.category === "Regex"}>{suggestion.category}</span
                >
              </div>
              <div class="text-xs text-base-content/70 mt-1">
                {suggestion.description}
              </div>
            </div>
          {:else if autocompleteType === "/" && typeof suggestion === "string"}
            <div class="flex-1">
              <code class="text-secondary font-mono">{suggestion}</code>
            </div>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</form>

<style>
  .query-expanded-overlay {
    min-width: 400px;
    max-width: 600px;
    width: 100%;
    max-height: 0;
    opacity: 0;
    transition:
      max-height 0.3s ease-in-out,
      opacity 0.3s ease-in-out;
  }

  .query-expanded-overlay.expanded {
    max-height: 500px;
    opacity: 1;
  }

  .query-expanded-overlay.collapsed {
    max-height: 0;
    opacity: 0;
  }

  .query-container {
    position: relative;
  }

  .suggestion-item {
    border-bottom: 1px solid var(--fallback-bc, oklch(var(--bc) / 0.1));
  }

  .suggestion-item:last-child {
    border-bottom: none;
  }

  .suggestion-item.selected {
    outline: 2px solid var(--fallback-p, oklch(var(--p)));
    outline-offset: -2px;
  }

  .autocomplete-dropdown {
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  }

  /* Custom scrollbar for autocomplete dropdown */
  .autocomplete-dropdown::-webkit-scrollbar {
    width: 8px;
  }

  .autocomplete-dropdown::-webkit-scrollbar-track {
    background: var(--fallback-b2, oklch(var(--b2)));
    border-radius: 4px;
  }

  .autocomplete-dropdown::-webkit-scrollbar-thumb {
    background: var(--fallback-bc, oklch(var(--bc) / 0.3));
    border-radius: 4px;
  }

  .autocomplete-dropdown::-webkit-scrollbar-thumb:hover {
    background: var(--fallback-bc, oklch(var(--bc) / 0.5));
  }
</style>
