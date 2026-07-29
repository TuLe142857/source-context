/**
 * Types for features the backend does not expose yet (see "Missing-API
 * Items" in plans/frontend_dev_plan.md). Shapes are this app's own best
 * guess at what a future endpoint would need — adjust once the real
 * contract exists.
 */
import type { SourceLanguage } from './project';

export interface UpdateRepositoryRequest {
  name: string;
}

export interface UpdateBranchRequest {
  commit_hashed: string;
}

export interface UpdateProjectRequest {
  root_dir: string;
  language: SourceLanguage;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface UpdateProfileRequest {
  username?: string;
  full_name?: string;
  email?: string;
}
