/**
 * src/lib/types.ts
 *
 * This file contains TypeScript type definitions used across the application.
 * It's been updated to reflect the `DocumentQueryResponse` structure
 * as defined in the OpenAPI specification, which returns a 'count'
 * and a 'documents' array.
 */

// Represents a single MongoDB document, which can have any key-value pairs.
// The _id is explicitly defined as a string, as it's a critical identifier.
export interface Document {
  _id: string;
  [key: string]: any;
}

export interface DatabaseListItem {
  name: string;
  opaque_id: string;
}

export interface PaginatedDatabases {
  databases: DatabaseListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface Collection {
  name: string;
  opaque_id: string;
}

export interface PaginatedCollections {
  database: {
    name: string;
    opaque_id: string;
  };
  collections: Collection[];
  total: number;
  page: number;
  page_size: number;
}

export interface GridFSBucket {
  bucket_name: string;
  opaque_id: string;
}

export interface PaginatedGridFSBuckets {
  database: {
    name: string;
    opaque_id: string;
  };
  buckets: GridFSBucket[];
  total: number;
  page: number;
  page_size: number;
}

// Adjusted to match the OpenAPI spec's response for querying documents.
// It returns a 'documents' array and a 'count' of total results.
export interface DocumentQueryResponse {
  documents: Document[];
  count: number;
}

export interface BreadcrumbSegment {
  name: string;
  href?: string;
  label?: string;
  isHome?: boolean;
  loading?: boolean;
}

