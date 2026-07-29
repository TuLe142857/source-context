/** Canonical languages supported by the indexing pipeline (backend SourceLanguage enum). */
export type SourceLanguage = 'python' | 'javascript' | 'typescript';

export const SOURCE_LANGUAGES: SourceLanguage[] = ['python', 'javascript', 'typescript'];

/**
 * A "Project" in backend vocabulary is a sub-project / SCIP indexing target
 * nested under a Branch (a root_dir + language pair) — NOT the same concept
 * as this app's Workspace. Labeled "Sub-project" in the UI to avoid confusion.
 */
export interface ProjectResponse {
  id: number;
  branch_id: number;
  workspace_id?: number | null;
  root_dir: string;
  language: SourceLanguage;
}

export interface ProjectCreateRequest {
  root_dir: string;
  language: SourceLanguage;
}
