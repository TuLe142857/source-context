/** Personal Access Tokens ("API Keys"), backend tag "Personal Access Tokens (API Keys)". */

export interface PATCreateRequest {
  name: string;
  expires_in_days?: number | null;
}

/** Returned ONCE at creation time — raw_token is never retrievable again. */
export interface PATCreateResponse {
  id: number;
  name: string;
  raw_token: string;
  token_prefix: string;
  expired_at?: string | null;
  expires_at?: string | null;
}

/** Returned by list — no raw_token, metadata only. */
export interface PATResponse {
  id: number;
  name: string;
  token_prefix: string;
  last_used_at?: string | null;
  expired_at?: string | null;
  expires_at?: string | null;
  is_revoked: boolean;
}
