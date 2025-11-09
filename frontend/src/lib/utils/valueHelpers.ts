/**
 * Value Helpers for MongoDB Queries
 * Provides DateTime helpers, common values, expandables, and utilities
 */

export interface ValueHelper {
  key: string;
  category: string;
  description: string;
  template: string;
  cursorOffset?: number;
  selectLength?: number;
}

/**
 * Get current date/time in various formats
 */
function getCurrentDate(): Date {
  return new Date();
}

function getTodayStart(): Date {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  return date;
}

function getTodayEnd(): Date {
  const date = new Date();
  date.setHours(23, 59, 59, 999);
  return date;
}

function getYesterdayStart(): Date {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  date.setHours(0, 0, 0, 0);
  return date;
}

function getWeekAgo(): Date {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date;
}

function getMonthStart(): Date {
  const date = new Date();
  date.setDate(1);
  date.setHours(0, 0, 0, 0);
  return date;
}

function getMonthEnd(): Date {
  const date = new Date();
  date.setMonth(date.getMonth() + 1);
  date.setDate(0);
  date.setHours(23, 59, 59, 999);
  return date;
}

function formatISODate(date: Date): string {
  return date.toISOString();
}

/**
 * Generate UUID v4
 */
function generateUUID(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Value helpers catalog - Streamlined essentials
 */
export const valueHelpers: ValueHelper[] = [
  // ==================== DATETIME HELPERS ====================
  {
    key: "now",
    category: "DateTime",
    description: "Current date and time (ISO string)",
    template: `"${formatISODate(getCurrentDate())}"`,
  },
  {
    key: "today",
    category: "DateTime",
    description: "Start of today (00:00:00)",
    template: `"${formatISODate(getTodayStart())}"`,
  },
  {
    key: "yesterday",
    category: "DateTime",
    description: "Start of yesterday",
    template: `"${formatISODate(getYesterdayStart())}"`,
  },
  {
    key: "weekAgo",
    category: "DateTime",
    description: "7 days ago from now",
    template: `"${formatISODate(getWeekAgo())}"`,
  },
  {
    key: "monthStart",
    category: "DateTime",
    description: "Start of current month",
    template: `"${formatISODate(getMonthStart())}"`,
  },
  {
    key: "lastWeek",
    category: "DateTime",
    description: "Last 7 days range",
    template: `{ "$gte": "${formatISODate(getWeekAgo())}", "$lte": "${formatISODate(getCurrentDate())}" }`,
  },

  // ==================== COMMON VALUES ====================
  {
    key: "null",
    category: "Common",
    description: "Null value",
    template: "null",
  },
  {
    key: "true",
    category: "Common",
    description: "Boolean true",
    template: "true",
  },
  {
    key: "false",
    category: "Common",
    description: "Boolean false",
    template: "false",
  },
  {
    key: "emptyString",
    category: "Common",
    description: "Empty string",
    template: '""',
  },
  {
    key: "emptyArray",
    category: "Common",
    description: "Empty array",
    template: "[]",
  },
  {
    key: "emptyObject",
    category: "Common",
    description: "Empty object",
    template: "{}",
  },

  // ==================== EXPANDABLES ====================
  {
    key: "array",
    category: "Expandable",
    description: "Array with placeholder items",
    template: '[ "item1", "item2" ]',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    key: "object",
    category: "Expandable",
    description: "Object with placeholder key-value",
    template: '{ "key": "value" }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== IDENTIFIERS ====================
  {
    key: "uuid",
    category: "Identifier",
    description: "Generate UUID v4",
    template: `"${generateUUID()}"`,
  },

  // ==================== NUMERIC HELPERS ====================
  {
    key: "zero",
    category: "Numeric",
    description: "Number zero",
    template: "0",
  },
];

/**
 * Get all unique categories
 */
export function getValueCategories(): string[] {
  const categories = new Set(valueHelpers.map((vh) => vh.category));
  return Array.from(categories).sort();
}

/**
 * Get value helpers by category
 */
export function getValueHelpersByCategory(category: string): ValueHelper[] {
  return valueHelpers.filter((vh) => vh.category === category);
}

/**
 * Search value helpers by text
 */
export function searchValueHelpers(searchTerm: string): ValueHelper[] {
  const term = searchTerm.toLowerCase();
  return valueHelpers.filter(
    (vh) =>
      vh.key.toLowerCase().includes(term) ||
      vh.description.toLowerCase().includes(term)
  );
}

/**
 * Get value helper by exact key
 */
export function getValueHelper(key: string): ValueHelper | undefined {
  return valueHelpers.find((vh) => vh.key === key);
}

/**
 * Refresh dynamic values (for DateTime helpers that need current time)
 */
export function refreshDynamicValues(): ValueHelper[] {
  return valueHelpers.map((vh) => {
    if (vh.category === "DateTime") {
      // Regenerate templates with current date/time
      switch (vh.key) {
        case "now":
          return {
            ...vh,
            template: `"${formatISODate(getCurrentDate())}"`,
          };
        case "today":
          return {
            ...vh,
            template: `"${formatISODate(getTodayStart())}"`,
          };
        case "yesterday":
          return {
            ...vh,
            template: `"${formatISODate(getYesterdayStart())}"`,
          };
        case "weekAgo":
          return {
            ...vh,
            template: `"${formatISODate(getWeekAgo())}"`,
          };
        case "monthStart":
          return {
            ...vh,
            template: `"${formatISODate(getMonthStart())}"`,
          };
        case "lastWeek":
          return {
            ...vh,
            template: `{ "$gte": "${formatISODate(getWeekAgo())}", "$lte": "${formatISODate(getCurrentDate())}" }`,
          };
      }
    } else if (vh.key === "uuid") {
      // Regenerate UUID
      return {
        ...vh,
        template: `"${generateUUID()}"`,
      };
    }
    return vh;
  });
}
