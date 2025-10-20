/**
 * Metadata utilities for filtering and managing memory metadata
 */

/**
 * System metadata fields that are managed by the backend
 * and should not be displayed or edited by users
 */
export const SYSTEM_METADATA_FIELDS = [
  'user_id',
  'agent_id',
  'run_id',
  'actor_id',
  'role',
  'source_app',
  'mcp_client'
] as const;

/**
 * Filters out system metadata fields and returns only custom user metadata
 * @param metadata - The complete metadata object
 * @returns Custom metadata only, or null if no custom fields exist
 */
export function getCustomMetadata(metadata?: Record<string, any>): Record<string, any> | null {
  if (!metadata) return null;

  const customMetadata: Record<string, any> = {};
  Object.keys(metadata).forEach(key => {
    if (!SYSTEM_METADATA_FIELDS.includes(key as any)) {
      customMetadata[key] = metadata[key];
    }
  });

  return Object.keys(customMetadata).length > 0 ? customMetadata : null;
}

/**
 * Validates that metadata doesn't contain system fields
 * @param metadata - Metadata to validate
 * @returns Error message if invalid, null if valid
 */
export function validateCustomMetadata(metadata: Record<string, any>): string | null {
  const systemFieldsFound = Object.keys(metadata).filter(key =>
    SYSTEM_METADATA_FIELDS.includes(key as any)
  );

  if (systemFieldsFound.length > 0) {
    return `Cannot modify system fields: ${systemFieldsFound.join(', ')}`;
  }

  return null;
}
