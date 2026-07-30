import { notImplemented } from './template';
import type { IndexingJobResponse } from './types/indexing';

/**
 * Indexing only exists at workspace/branch granularity on the backend today
 * (see branches.api.ts / indexing.api.ts) — there is no per-project reindex
 * endpoint. Kept as its own template action per product decision, rather
 * than silently remapping to the parent branch's real reindex call.
 */
export function reindexProjectApi(_workspaceId: number, _projectId: number): Promise<IndexingJobResponse> {
  return notImplemented('Reindex riêng cho sub-project này');
}
