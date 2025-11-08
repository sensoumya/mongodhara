/**
 * Query Autocomplete Utilities
 * Handles cursor tracking, trigger detection, text insertion for intelligent query editing
 */

export interface TriggerInfo {
  type: "@" | "/" | "#" | null;
  position: number;
  searchText: string;
}

export interface CursorPosition {
  start: number;
  end: number;
}

/**
 * Get current cursor position in a text input/textarea
 */
export function getCursorPosition(
  element: HTMLInputElement | HTMLTextAreaElement
): CursorPosition {
  return {
    start: element.selectionStart || 0,
    end: element.selectionEnd || 0,
  };
}

/**
 * Set cursor position in a text input/textarea
 */
export function setCursorPosition(
  element: HTMLInputElement | HTMLTextAreaElement,
  position: number
): void {
  element.setSelectionRange(position, position);
  element.focus();
}

/**
 * Detect if user has typed a trigger character (@, /, or #)
 * Returns trigger info including the search text after trigger
 */
export function detectTrigger(
  text: string,
  cursorPosition: number
): TriggerInfo {
  if (cursorPosition === 0) {
    return { type: null, position: 0, searchText: "" };
  }

  const textBeforeCursor = text.substring(0, cursorPosition);

  // Find the last occurrence of @, /, or #
  const lastAt = textBeforeCursor.lastIndexOf("@");
  const lastSlash = textBeforeCursor.lastIndexOf("/");
  const lastHash = textBeforeCursor.lastIndexOf("#");

  // Determine which trigger is most recent
  const triggerPos = Math.max(lastAt, lastSlash, lastHash);

  if (triggerPos === -1) {
    return { type: null, position: 0, searchText: "" };
  }

  const triggerChar = textBeforeCursor[triggerPos];
  const searchText = textBeforeCursor.substring(triggerPos + 1);

  // Check if trigger is valid (not inside quotes or after alphanumeric)
  const charBeforeTrigger =
    triggerPos > 0 ? textBeforeCursor[triggerPos - 1] : " ";
  const isValidContext =
    /[\s\{\[\,\:]/.test(charBeforeTrigger) || triggerPos === 0;

  if (!isValidContext) {
    return { type: null, position: 0, searchText: "" };
  }

  // Check if there's a space after trigger (which would invalidate it)
  if (searchText.includes(" ") || searchText.includes("\n")) {
    return { type: null, position: 0, searchText: "" };
  }

  return {
    type: triggerChar as "@" | "/" | "#",
    position: triggerPos,
    searchText: searchText,
  };
}

/**
 * Insert text at cursor position and optionally select placeholder text
 */
export function insertTextAtCursor(
  element: HTMLInputElement | HTMLTextAreaElement,
  textToInsert: string,
  triggerPosition: number,
  searchTextLength: number,
  cursorOffset?: number,
  selectLength?: number
): void {
  const currentValue = element.value;

  // Remove the trigger character and search text, then insert new text
  const before = currentValue.substring(0, triggerPosition);
  const after = currentValue.substring(triggerPosition + 1 + searchTextLength);

  const newValue = before + textToInsert + after;
  element.value = newValue;

  // Calculate new cursor position
  let newCursorPos = triggerPosition + textToInsert.length;
  if (cursorOffset !== undefined) {
    newCursorPos = triggerPosition + cursorOffset;
  }

  // If selectLength is provided, select that range of text
  if (selectLength !== undefined && selectLength > 0) {
    element.setSelectionRange(newCursorPos, newCursorPos + selectLength);
  } else {
    setCursorPosition(element, newCursorPos);
  }

  element.focus();

  // Trigger input event for reactivity
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

/**
 * Check if cursor is between empty quotes and auto-trigger field suggestions
 */
export function isInEmptyQuotes(
  text: string,
  cursorPosition: number
): boolean {
  if (cursorPosition === 0 || cursorPosition >= text.length) {
    return false;
  }

  const charBefore = text[cursorPosition - 1];
  const charAfter = text[cursorPosition];

  // Check if cursor is between two quotes: ""|""
  return charBefore === '"' && charAfter === '"';
}

/**
 * Detect if cursor is in a position where field name should be suggested
 */
export function shouldAutoTriggerFields(
  text: string,
  cursorPosition: number
): boolean {
  // Check if in empty quotes
  if (isInEmptyQuotes(text, cursorPosition)) {
    return true;
  }

  // Check if just after opening brace: { "
  const textBeforeCursor = text.substring(0, cursorPosition);
  const lastOpenBrace = textBeforeCursor.lastIndexOf("{");
  if (lastOpenBrace !== -1) {
    const textAfterBrace = textBeforeCursor.substring(lastOpenBrace + 1).trim();
    if (textAfterBrace === '"' || textAfterBrace === "") {
      return true;
    }
  }

  return false;
}

/**
 * Calculate dropdown position based on cursor position in element
 * This is a simplified version - may need enhancement for complex layouts
 */
export function calculateDropdownPosition(
  element: HTMLInputElement | HTMLTextAreaElement,
  triggerPosition: number
): { top: number; left: number } {
  const rect = element.getBoundingClientRect();

  // For input elements, position dropdown below
  if (element.tagName === "INPUT") {
    return {
      top: rect.bottom + 4,
      left: rect.left,
    };
  }

  // For textarea, try to calculate position based on text content
  // This is approximate - perfect positioning would need a canvas measurement
  const textBeforeCursor = element.value.substring(0, triggerPosition);
  const lines = textBeforeCursor.split("\n");
  const currentLine = lines.length;
  const lineHeight = parseInt(getComputedStyle(element).lineHeight) || 20;

  // Get scrollTop to account for scrolled content
  const scrollTop = element.scrollTop;

  return {
    top: rect.top + currentLine * lineHeight - scrollTop + 4,
    left: rect.left + 8, // Small offset from left
  };
}

/**
 * Filter items based on search text
 */
export function filterItems<T>(
  items: T[],
  searchText: string,
  getSearchableText: (item: T) => string
): T[] {
  if (!searchText) {
    return items;
  }

  const lowerSearch = searchText.toLowerCase();
  return items.filter((item) =>
    getSearchableText(item).toLowerCase().includes(lowerSearch)
  );
}

/**
 * Get the word at cursor position (for context-aware suggestions)
 */
export function getWordAtCursor(text: string, cursorPosition: number): string {
  // Find word boundaries
  let start = cursorPosition;
  let end = cursorPosition;

  // Move start backward to find word start
  while (start > 0 && /[\w$]/.test(text[start - 1])) {
    start--;
  }

  // Move end forward to find word end
  while (end < text.length && /[\w$]/.test(text[end])) {
    end++;
  }

  return text.substring(start, end);
}

/**
 * Check if cursor is inside a string (between quotes)
 */
export function isInsideString(text: string, cursorPosition: number): boolean {
  const textBeforeCursor = text.substring(0, cursorPosition);

  let inString = false;
  let escapeNext = false;

  for (let i = 0; i < textBeforeCursor.length; i++) {
    const char = textBeforeCursor[i];

    if (escapeNext) {
      escapeNext = false;
      continue;
    }

    if (char === "\\") {
      escapeNext = true;
      continue;
    }

    if (char === '"') {
      inString = !inString;
    }
  }

  return inString;
}

/**
 * Format JSON with proper indentation
 */
export function beautifyJSON(jsonString: string): string {
  try {
    const parsed = JSON.parse(jsonString);
    return JSON.stringify(parsed, null, 2);
  } catch (e) {
    return jsonString; // Return original if parsing fails
  }
}

/**
 * Validate JSON string and provide detailed error information
 */
export function validateJSON(jsonString: string): {
  valid: boolean;
  error?: string;
  line?: number;
  column?: number;
} {
  if (!jsonString.trim()) {
    return { valid: true };
  }

  try {
    JSON.parse(jsonString);
    return { valid: true };
  } catch (e: any) {
    // Extract line and column from error message if available
    // Error messages typically look like: "Unexpected token } in JSON at position 25"
    let line: number | undefined;
    let column: number | undefined;
    
    if (e.message && typeof e.message === 'string') {
      // Try to extract position
      const posMatch = e.message.match(/position (\d+)/);
      if (posMatch) {
        const position = parseInt(posMatch[1]);
        // Calculate line and column from position
        const lines = jsonString.substring(0, position).split('\n');
        line = lines.length;
        column = lines[lines.length - 1].length + 1;
      }
    }
    
    let errorMsg = e.message;
    if (line && column) {
      errorMsg = `Line ${line}, Column ${column}: ${e.message}`;
    }
    
    return { valid: false, error: errorMsg, line, column };
  }
}
