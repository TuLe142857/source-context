/** Mirrors backend UserResponse. Note: is_active is a string in the backend schema, not boolean. */
export interface UserResponse {
  id: number;
  email: string;
  username: string;
  full_name?: string | null;
  is_active: string;
}

export interface UserRegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface UserLoginRequest {
  username_or_email: string;
  password: string;
}

/** Mirrors backend TokenResponse, returned by both /auth/register and /auth/login. */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}
