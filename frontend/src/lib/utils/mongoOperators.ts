/**
 * MongoDB Query Operators Catalog
 * Comprehensive list of MongoDB operators with templates for autocomplete
 */

export interface MongoOperator {
  operator: string;
  category: string;
  description: string;
  template: string;
  cursorOffset?: number; // Character offset from start of template to place cursor
  selectLength?: number; // Length of text to auto-select after insertion
}

export const mongoOperators: MongoOperator[] = [
  // ==================== COMPARISON OPERATORS ====================
  {
    operator: "$eq",
    category: "Comparison",
    description: "Matches values that are equal to a specified value",
    template: '{ "field": { "$eq": "value" } }',
    cursorOffset: 2, // Position cursor before opening quote
    selectLength: 7, // Select "field" including quotes for easy replacement
  },
  {
    operator: "$ne",
    category: "Comparison",
    description: "Matches all values that are not equal to a specified value",
    template: '{ "field": { "$ne": "value" } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$gt",
    category: "Comparison",
    description: "Matches values that are greater than a specified value",
    template: '{ "field": { "$gt": 0 } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$gte",
    category: "Comparison",
    description: "Matches values that are greater than or equal to a specified value",
    template: '{ "field": { "$gte": 0 } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$lt",
    category: "Comparison",
    description: "Matches values that are less than a specified value",
    template: '{ "field": { "$lt": 0 } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$lte",
    category: "Comparison",
    description: "Matches values that are less than or equal to a specified value",
    template: '{ "field": { "$lte": 0 } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$in",
    category: "Comparison",
    description: "Matches any of the values specified in an array",
    template: '{ "field": { "$in": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$nin",
    category: "Comparison",
    description: "Matches none of the values specified in an array",
    template: '{ "field": { "$nin": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== LOGICAL OPERATORS ====================
  {
    operator: "$and",
    category: "Logical",
    description: "Joins query clauses with a logical AND",
    template: '{ "$and": [ {}, {} ] }',
    cursorOffset: 13, // Inside first object
  },
  {
    operator: "$or",
    category: "Logical",
    description: "Joins query clauses with a logical OR",
    template: '{ "$or": [ {}, {} ] }',
    cursorOffset: 12,
  },
  {
    operator: "$nor",
    category: "Logical",
    description: "Joins query clauses with a logical NOR",
    template: '{ "$nor": [ {}, {} ] }',
    cursorOffset: 13,
  },
  {
    operator: "$not",
    category: "Logical",
    description: "Inverts the effect of a query expression",
    template: '{ "field": { "$not": {} } }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== ELEMENT OPERATORS ====================
  {
    operator: "$exists",
    category: "Element",
    description: "Matches documents that have the specified field",
    template: '{ "field": { "$exists": true } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$type",
    category: "Element",
    description: "Selects documents if a field is of the specified type",
    template: '{ "field": { "$type": "string" } }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== EVALUATION OPERATORS ====================
  {
    operator: "$regex",
    category: "Evaluation",
    description: "Selects documents where values match a specified regular expression",
    template: '{ "field": { "$regex": "pattern", "$options": "i" } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$expr",
    category: "Evaluation",
    description: "Allows use of aggregation expressions within the query language",
    template: '{ "$expr": { "$gt": [ "$field1", "$field2" ] } }',
    cursorOffset: 21,
  },
  {
    operator: "$jsonSchema",
    category: "Evaluation",
    description: "Validate documents against the given JSON Schema",
    template: '{ "$jsonSchema": { "required": [ "field" ] } }',
    cursorOffset: 17,
  },
  {
    operator: "$mod",
    category: "Evaluation",
    description: "Performs a modulo operation on the value of a field",
    template: '{ "field": { "$mod": [ 4, 0 ] } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$text",
    category: "Evaluation",
    description: "Performs text search",
    template: '{ "$text": { "$search": "search text" } }',
    cursorOffset: 25,
  },
  {
    operator: "$where",
    category: "Evaluation",
    description: "Matches documents that satisfy a JavaScript expression",
    template: '{ "$where": "this.field1 === this.field2" }',
    cursorOffset: 13,
  },

  // ==================== ARRAY OPERATORS ====================
  {
    operator: "$all",
    category: "Array",
    description: "Matches arrays that contain all elements specified in the query",
    template: '{ "field": { "$all": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$elemMatch",
    category: "Array",
    description: "Matches documents that contain an array field with at least one element matching criteria",
    template: '{ "field": { "$elemMatch": {} } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$size",
    category: "Array",
    description: "Matches arrays with a specified number of elements",
    template: '{ "field": { "$size": 0 } }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== GEOSPATIAL OPERATORS ====================
  {
    operator: "$geoWithin",
    category: "Geospatial",
    description: "Selects geometries within a bounding GeoJSON geometry",
    template: '{ "location": { "$geoWithin": { "$geometry": { "type": "Polygon", "coordinates": [[]] } } } }',
    cursorOffset: 2,
    selectLength: 10,
  },
  {
    operator: "$geoIntersects",
    category: "Geospatial",
    description: "Selects geometries that intersect with a GeoJSON geometry",
    template: '{ "location": { "$geoIntersects": { "$geometry": { "type": "Point", "coordinates": [] } } } }',
    cursorOffset: 2,
    selectLength: 10,
  },
  {
    operator: "$near",
    category: "Geospatial",
    description: "Returns geospatial objects in proximity to a point",
    template: '{ "location": { "$near": { "$geometry": { "type": "Point", "coordinates": [] }, "$maxDistance": 1000 } } }',
    cursorOffset: 2,
    selectLength: 10,
  },
  {
    operator: "$nearSphere",
    category: "Geospatial",
    description: "Returns geospatial objects in proximity to a point on a sphere",
    template: '{ "location": { "$nearSphere": { "$geometry": { "type": "Point", "coordinates": [] }, "$maxDistance": 1000 } } }',
    cursorOffset: 2,
    selectLength: 10,
  },

  // ==================== BITWISE OPERATORS ====================
  {
    operator: "$bitsAllClear",
    category: "Bitwise",
    description: "Matches numeric or binary values where all bit positions are clear",
    template: '{ "field": { "$bitsAllClear": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$bitsAllSet",
    category: "Bitwise",
    description: "Matches numeric or binary values where all bit positions are set",
    template: '{ "field": { "$bitsAllSet": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$bitsAnyClear",
    category: "Bitwise",
    description: "Matches numeric or binary values where any bit position is clear",
    template: '{ "field": { "$bitsAnyClear": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$bitsAnySet",
    category: "Bitwise",
    description: "Matches numeric or binary values where any bit position is set",
    template: '{ "field": { "$bitsAnySet": [] } }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== PROJECTION OPERATORS ====================
  {
    operator: "$",
    category: "Projection",
    description: "Projects the first element in an array that matches the query condition",
    template: '{ "field.$": 1 }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "$slice",
    category: "Projection",
    description: "Limits the number of elements projected from an array",
    template: '{ "field": { "$slice": 5 } }',
    cursorOffset: 2,
    selectLength: 7,
  },

  // ==================== COMMON QUERY PATTERNS ====================
  {
    operator: "$and pattern",
    category: "Patterns",
    description: "Combine multiple query conditions with AND logic",
    template: '{ "$and": [ { "field1": "value1" }, { "field2": "value2" } ] }',
    cursorOffset: 13,
    selectLength: 8,
  },
  {
    operator: "$or pattern",
    category: "Patterns",
    description: "Combine multiple query conditions with OR logic",
    template: '{ "$or": [ { "field1": "value1" }, { "field2": "value2" } ] }',
    cursorOffset: 12,
    selectLength: 8,
  },
  {
    operator: "text search",
    category: "Patterns",
    description: "Full-text search query",
    template: '{ "$text": { "$search": "search terms" } }',
    cursorOffset: 25,
    selectLength: 14,
  },
  {
    operator: "regex pattern",
    category: "Patterns",
    description: "Regular expression pattern match",
    template: '{ "field": { "$regex": "pattern", "$options": "i" } }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "sort ascending",
    category: "Patterns",
    description: "Sort results in ascending order by field",
    template: '{ "field": 1 }',
    cursorOffset: 2,
    selectLength: 7,
  },
  {
    operator: "sort descending",
    category: "Patterns",
    description: "Sort results in descending order by field",
    template: '{ "field": -1 }',
    cursorOffset: 2,
    selectLength: 7,
  },
];

/**
 * Get all unique categories
 */
export function getCategories(): string[] {
  const categories = new Set(mongoOperators.map((op) => op.category));
  return Array.from(categories).sort();
}

/**
 * Get operators by category
 */
export function getOperatorsByCategory(category: string): MongoOperator[] {
  return mongoOperators.filter((op) => op.category === category);
}

/**
 * Search operators by text (operator name or description)
 */
export function searchOperators(searchTerm: string): MongoOperator[] {
  const term = searchTerm.toLowerCase();
  return mongoOperators.filter(
    (op) =>
      op.operator.toLowerCase().includes(term) ||
      op.description.toLowerCase().includes(term)
  );
}

/**
 * Get operator by exact name
 */
export function getOperator(operatorName: string): MongoOperator | undefined {
  return mongoOperators.find((op) => op.operator === operatorName);
}
