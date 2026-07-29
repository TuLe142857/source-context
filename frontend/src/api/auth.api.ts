import { http } from './http';
import type { TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse } from './types/auth';

export function registerApi(data: UserRegisterRequest): Promise<TokenResponse> {
  return http.post<TokenResponse>('/auth/register', data).then((res) => res.data);
}

export function loginApi(data: UserLoginRequest): Promise<TokenResponse> {
  return http.post<TokenResponse>('/auth/login', data).then((res) => res.data);
}

export function getMeApi(): Promise<UserResponse> {
  return http.get<UserResponse>('/auth/me').then((res) => res.data);
}
