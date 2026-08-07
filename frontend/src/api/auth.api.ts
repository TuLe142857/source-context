import { http } from './http';
import type {
  RegisterRequest,
  RegisterVerifyRequest,
  TokenResponse,
  UserLoginRequest,
  UserResponse,
} from './types/auth';

/** Step 1: sends an OTP to the given email. */
export function registerApi(data: RegisterRequest): Promise<void> {
  return http.post<void>('/auth/register', data).then((res) => res.data);
}

/** Step 2: verifies the OTP and creates the account. */
export function registerVerifyOtpApi(data: RegisterVerifyRequest): Promise<TokenResponse> {
  return http.post<TokenResponse>('/auth/register/verify-otp', data).then((res) => res.data);
}

export function loginApi(data: UserLoginRequest): Promise<TokenResponse> {
  return http.post<TokenResponse>('/auth/login', data).then((res) => res.data);
}

export function getMeApi(): Promise<UserResponse> {
  return http.get<UserResponse>('/auth/me').then((res) => res.data);
}
