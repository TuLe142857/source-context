import { http } from './http';

export interface GitHubLinkInstallationPayload {
  installation_id: number;
  workspace_id?: number;
}

export async function linkGitHubInstallation(
  payload: GitHubLinkInstallationPayload
) {
  const res = await http.post('/webhooks/link', payload);
  return res.data;
}
