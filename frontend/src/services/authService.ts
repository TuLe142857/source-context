import { fetchApi } from './api';
import type { User } from '../types';

export async function loginApi(username: string, password: string): Promise<{ access_token: string; token_type: string }> {
  return fetchApi<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      username_or_email: username,
      password: password,
    }),
  });
}

export async function registerApi(data: {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}): Promise<User> {
  return fetchApi<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getMeApi(): Promise<User> {
  return fetchApi<User>('/auth/me');
}
