<script lang="ts">
  import {
    defaultKeymap,
    history,
    historyKeymap,
    indentWithTab,
  } from "@codemirror/commands";
  import { json } from "@codemirror/lang-json";
  import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
  import { lintGutter, linter } from "@codemirror/lint";
  import { EditorView, keymap } from "@codemirror/view";
  import { tags } from "@lezer/highlight";
  import { basicSetup } from "codemirror";
  import jsonlint from "jsonlint-mod";
  import { createEventDispatcher, onDestroy, onMount } from "svelte";

  export let isOpen: boolean = false;
  export let document: any = {};
  export let readOnly: boolean = false;
  const dispatch = createEventDispatcher();

  let editorContainer: HTMLElement;
  let editorView: EditorView | null = null;
  let panelElement: HTMLElement;
  let isExpanded = false;
  let minWidth = 400;
  let panelWidth = 600;
  let showAlert = false;
  let alertMessage = "";
  let jsonString: string;
  let copySuccess = false;

  // Custom theme to enforce full height
  const fullHeightTheme = EditorView.theme({
    "&": { height: "100%" },
    ".cm-scroller": { minHeight: "100%" },
    ".cm-content": { minHeight: "100%" },
    ".cm-gutters": { minHeight: "100%" },
  });

  // DaisyUI Theme Extension - Minimal theme, let global CSS handle selection
  const daisyUITheme = EditorView.theme({
    "&": {
      backgroundColor: "hsl(var(--b1))",
      color: "hsl(var(--bc))",
    },
    ".cm-scroller": {
      backgroundColor: "hsl(var(--b1))",
    },
    ".cm-gutters": {
      backgroundColor: "hsl(var(--b2))",
      // color: "hsl(var(--bc) / 0.7)",
      borderRight: "1px solid hsl(var(--b3))",
    },
    ".cm-selectionBackground": {
      backgroundColor: "rgba(107, 114, 128, 0.2) !important",
    },
    "&.cm-focused .cm-selectionBackground": {
      backgroundColor: "rgba(107, 114, 128, 0.2) !important",
    },
    "::selection": {
      backgroundColor: "rgba(107, 114, 128, 0.2) !important",
    },
    ".cm-activeLine": {
      backgroundColor: "hsl(var(--b3))",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "hsl(var(--b3))",
    },
    ".cm-lint-marker": {
      borderColor: "transparent",
    },
    ".cm-cursor": {
      borderLeftColor: "hsl(var(--bc))",
    },
    ".cm-searchMatch": {
      backgroundColor: "hsl(var(--wa) / 0.3)",
      outline: "1px solid hsl(var(--wa) / 0.5)",
    },
    ".cm-searchMatch.cm-searchMatch-selected": {
      backgroundColor: "hsl(var(--wa) / 0.5)",
    },
  });

  // JSON Syntax Highlighting Theme - balanced colors for both light and dark themes
  const jsonHighlightStyle = HighlightStyle.define([
    { tag: tags.propertyName, class: "text-base-content/70 font-medium" },
    { tag: tags.string, class: "text-primary" },
    { tag: tags.number, class: "text-secondary" },
    { tag: tags.bool, class: "text-accent font-bold" },
    { tag: tags.null, class: "text-warning font-bold" },
    { tag: tags.keyword, class: "text-info font-bold" },
  ]);

  // Sync external doc -> editor
  $: if (editorView && document && isOpen) {
    const newJsonString = JSON.stringify(document, null, 4);
    if (editorView.state.doc.toString() !== newJsonString) {
      editorView.dispatch({
        changes: {
          from: 0,
          to: editorView.state.doc.length,
          insert: newJsonString,
        },
      });
      jsonString = newJsonString;
    }
  }

  onMount(() => {
    if (window.innerWidth > 1024) panelWidth = window.innerWidth * 0.6;
    jsonString = JSON.stringify(document || {}, null, 4);
    initializeEditor();
  });

  onDestroy(() => editorView?.destroy());
  function initializeEditor() {
    if (!editorContainer) return;

    const extensions = [
      basicSetup,
      json(),
      syntaxHighlighting(jsonHighlightStyle),
      lintGutter(),
      linter((view) => {
        try {
          jsonlint.parse(view.state.doc.toString());
          return [];
        } catch (e: any) {
          // Extract line and column from error message if available
          let line = 1;
          let column = 1;

          // Try to parse line number from error message
          const lineMatch = e.message.match(/line (\d+)/i);
          if (lineMatch) {
            line = parseInt(lineMatch[1], 10);
          }

          // Try to parse column number from error message
          const columnMatch = e.message.match(/column (\d+)/i);
          if (columnMatch) {
            column = parseInt(columnMatch[1], 10);
          }

          // Calculate position in document
          const doc = view.state.doc;
          let pos = 0;

          try {
            // Find the actual position of the error
            if (line > 1) {
              for (let i = 1; i < line && pos < doc.length; i++) {
                const lineEnd = doc.lineAt(pos).to;
                pos = lineEnd + 1; // Move to start of next line
              }
            }

            // Add column offset
            pos += Math.max(0, column - 1);
            pos = Math.min(pos, doc.length);

            // Get the line at this position for error span
            const errorLine = doc.lineAt(pos);

            return [
              {
                from: errorLine.from,
                to: errorLine.to,
                severity: "error",
                message: e.message,
              },
            ];
          } catch (posError) {
            // Fallback to first line if position calculation fails
            const firstLine = doc.line(1);
            return [
              {
                from: firstLine.from,
                to: firstLine.to,
                severity: "error",
                message: e.message,
              },
            ];
          }
        }
      }),
      EditorView.lineWrapping,
      history(),
      keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
      fullHeightTheme,
      daisyUITheme,
    ];

    // Add readOnly extension if readOnly prop is true
    if (readOnly) {
      extensions.push(EditorView.editable.of(false));
    } else {
      extensions.push(
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            jsonString = update.state.doc.toString();
          }
        })
      );
    }

    editorView = new EditorView({
      doc: jsonString,
      extensions,
      parent: editorContainer,
    });
  }

  function toggleExpand() {
    isExpanded = !isExpanded;
    panelWidth = isExpanded ? window.innerWidth * 0.9 : window.innerWidth * 0.6;
  }

  function startResize(event: MouseEvent) {
    if (isExpanded) return;
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = panelElement.offsetWidth;

    function handleMouseMove(e: MouseEvent) {
      const newWidth = startWidth - (e.clientX - startX);
      panelWidth = Math.max(newWidth, minWidth);
    }
    function handleMouseUp() {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    }
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }

  function prettify() {
    try {
      const parsed = JSON.parse(editorView!.state.doc.toString());
      const pretty = JSON.stringify(parsed, null, 4);
      editorView!.dispatch({
        changes: { from: 0, to: editorView!.state.doc.length, insert: pretty },
      });
    } catch {
      alertMessage = "Invalid JSON format!";
      showAlert = true;
    }
  }

  async function copyToClipboard() {
    try {
      const content = editorView!.state.doc.toString();
      await navigator.clipboard.writeText(content);
      // Show tick mark for 2 seconds
      copySuccess = true;
      setTimeout(() => {
        copySuccess = false;
      }, 2000);
    } catch {
      alertMessage = "Failed to copy to clipboard!";
      showAlert = true;
    }
  }

  function save() {
    try {
      const parsed = JSON.parse(editorView!.state.doc.toString());
      dispatch("save", parsed);
    } catch {
      alertMessage = "Cannot save invalid JSON!";
      showAlert = true;
    }
  }

  function close() {
    isOpen = false;
    dispatch("close");
  }

  function handleBackdropClick(event: MouseEvent) {
    // Only close if clicking on the backdrop itself, not on child elements
    if (event.target === event.currentTarget) {
      close();
    }
  }

  function handleAlertClose() {
    showAlert = false;
    alertMessage = "";
  }

  $: currentPanelWidth = `${panelWidth}px`;
</script>

<div
  class="fixed inset-0"
  class:pointer-events-none={!isOpen}
  on:click={handleBackdropClick}
>
  <div
    class="absolute top-16 right-0 h-[calc(100vh-4rem)] bg-base-100 shadow-2xl transition-all duration-300 ease-in-out flex flex-row-reverse z-[9999]"
    class:translate-x-full={!isOpen}
    style="width: {currentPanelWidth};"
    bind:this={panelElement}
    on:click|stopPropagation
  >
    <div
      class="w-2 h-full cursor-col-resize absolute left-0 top-0 z-10 hover:bg-base-200 transition-colors"
      on:mousedown={startResize}
    ></div>

    <div class="flex flex-col flex-grow p-4">
      <div
        class="flex-grow w-full rounded-lg font-mono text-sm bg-base-200 text-base-content shadow-inner overflow-hidden border border-base-300"
        bind:this={editorContainer}
      ></div>

      <div class="flex justify-between space-x-3 pt-3 pb-4 px-0 mt-4">
        <div class="flex space-x-3">
          <div class="tooltip" data-tip="Close">
            <button
              on:click={close}
              class="btn btn-ghost btn-circle hover:text-accent hover:bg-base-200/80"
            >
              <i class="fas fa-times text-lg"></i>
            </button>
          </div>
          <div class="tooltip" data-tip={isExpanded ? "Collapse" : "Expand"}>
            <button
              on:click={toggleExpand}
              class="btn btn-ghost hover:text-accent hover:bg-base-200/80"
            >
              {#if isExpanded}
                <i class="fas fa-compress text-lg"></i>
              {:else}
                <i class="fas fa-expand text-lg"></i>
              {/if}
            </button>
          </div>
        </div>

        <div class="flex space-x-3">
          <div class="tooltip tooltip-left" data-tip="Copy Content">
            <button
              on:click={copyToClipboard}
              class="btn btn-ghost hover:text-secondary hover:bg-base-200/80"
            >
              {#if copySuccess}
                <i class="fas fa-check text-lg text-success"></i>
              {:else}
                <i class="fas fa-copy text-lg"></i>
              {/if}
            </button>
          </div>
          <div class="tooltip tooltip-left" data-tip="Reformat JSON">
            <button
              on:click={prettify}
              class="btn btn-ghost hover:text-secondary hover:bg-base-200/80"
            >
              <i class="fa-solid fa-wand-magic-sparkles text-lg"></i>
            </button>
          </div>
          {#if !readOnly}
            <div class="tooltip tooltip-left" data-tip="Save Document">
              <button on:click={save} class="btn btn-primary">
                <i class="fas fa-save text-lg"></i>
              </button>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

{#if showAlert}
  <div
    class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[100]"
  >
    <div
      class="bg-base-100 rounded-lg p-6 shadow-xl max-w-sm mx-auto text-center"
    >
      <p class="text-lg font-semibold mb-4">{alertMessage}</p>
      <button on:click={handleAlertClose} class="btn btn-primary">OK</button>
    </div>
  </div>
{/if}

<style>
  /* Global styles for CodeMirror, referencing DaisyUI CSS variables */
  :global(.cm-editor) {
    font-family: "Source Code Pro", monospace !important;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  :global(.cm-scroller),
  :global(.cm-content) {
    font-family: "Source Code Pro", monospace !important;
    font-size: 14px;
    line-height: 1.5;
    background-color: transparent !important; /* Managed by the JS theme */
    overflow-y: auto !important;
  }

  :global(.cm-lintRange-error) {
    background-color: hsl(var(--er) / 0.1);
  }

  :global(.cm-diagnostic-error) {
    color: hsl(var(--er));
  }

  /* Make CodeMirror tooltip text always black for better visibility */
  :global(.cm-tooltip) {
    color: black !important;
  }
</style>
