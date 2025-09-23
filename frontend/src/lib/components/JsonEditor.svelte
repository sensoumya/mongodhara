<script lang="ts">
  import {
    defaultKeymap,
    history,
    historyKeymap,
    indentWithTab,
  } from "@codemirror/commands";
  import { json } from "@codemirror/lang-json";
  import { lintGutter, linter } from "@codemirror/lint";
  import { EditorView, keymap } from "@codemirror/view";
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
      color: "hsl(var(--bc) / 0.7)",
      borderRight: "1px solid hsl(var(--b3))",
    },
    // Styles for the active line
    ".cm-activeLine": {
      backgroundColor: "hsl(var(--b3) / 0.6)",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "hsl(var(--b3) / 0.6)",
    },
    ".cm-lint-marker": {
      borderColor: "transparent",
    },
    // Cursor color
    ".cm-cursor": {
      borderLeftColor: "hsl(var(--bc))",
    },
    // Search highlight colors
    ".cm-searchMatch": {
      backgroundColor: "hsl(var(--wa) / 0.3)",
      outline: "1px solid hsl(var(--wa) / 0.5)",
    },
    ".cm-searchMatch.cm-searchMatch-selected": {
      backgroundColor: "hsl(var(--wa) / 0.5)",
    },
  });

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
      lintGutter(),
      linter((view) => {
        try {
          jsonlint.parse(view.state.doc.toString());
          return [];
        } catch (e: any) {
          return [
            {
              from: 0,
              to: view.state.doc.length,
              severity: "error",
              message: e.message,
            },
          ];
        }
      }),
      EditorView.lineWrapping,
      history(),
      keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
      fullHeightTheme,
      daisyUITheme, // Updated theme extension
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
            <button on:click={close} class="btn btn-ghost btn-circle">
              <i class="fas fa-times text-lg"></i>
            </button>
          </div>
          <div class="tooltip" data-tip={isExpanded ? "Collapse" : "Expand"}>
            <button on:click={toggleExpand} class="btn btn-ghost">
              {#if isExpanded}
                <i class="fas fa-compress text-lg"></i>
              {:else}
                <i class="fas fa-expand text-lg"></i>
              {/if}
            </button>
          </div>
        </div>

        <div class="flex space-x-3">
          {#if !readOnly}
            <div class="tooltip" data-tip="Reformat JSON">
              <button on:click={prettify} class="btn btn-ghost">
                <i class="fa-solid fa-wand-magic-sparkles text-lg"></i>
              </button>
            </div>
            <div class="tooltip" data-tip="Save Document">
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

  /* Updated JSON highlighting with better DaisyUI integration */
  :global(.cm-string) {
    color: hsl(var(--su));
    font-weight: 500;
  }
  :global(.cm-property) {
    color: hsl(var(--p));
    font-weight: 600;
  }
  :global(.cm-number) {
    color: hsl(var(--in));
    font-weight: 500;
  }
  :global(.cm-boolean),
  :global(.cm-null) {
    color: hsl(var(--se));
    font-weight: 600;
  }
  :global(.cm-punctuation) {
    color: hsl(var(--bc) / 0.9);
  }

  /* Brackets and braces styling */
  :global(.cm-bracket) {
    color: hsl(var(--bc) / 0.8);
    font-weight: bold;
  }

  /* Comment styles (if any) */
  :global(.cm-comment) {
    color: hsl(var(--bc) / 0.6);
    font-style: italic;
  }

  /* Line numbers styling */
  :global(.cm-lineNumbers) {
    color: hsl(var(--bc) / 0.5);
  }

  /* Fold markers */
  :global(.cm-foldMarker) {
    background-color: hsl(var(--b3));
    color: hsl(var(--bc));
    border: 1px solid hsl(var(--bc) / 0.3);
  }
</style>
