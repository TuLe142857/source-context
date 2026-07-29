import { http } from './http';
import type { PATCreateRequest, PATCreateResponse, PATResponse } from './types/tokens';

export function listPatsApi(): Promise<PATResponse[]> {
  return http.get<PATResponse[]>('/user/tokens').then((res) => res.data);
}

export function createPatApi(data: PATCreateRequest): Promise<PATCreateResponse> {
  return http.post<PATCreateResponse>('/user/tokens', data).then((res) => res.data);
}

export function revokePatApi(tokenId: number): Promise<void> {
  return http.delete(`/user/tokens/${tokenId}`).then(() => undefined);
}
