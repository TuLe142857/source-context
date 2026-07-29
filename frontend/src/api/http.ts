import axios, { type AxiosError } from 'axios';
import { ApiError, ErrorCode, type ApiErrorResponse } from './types/common';

/** Same localStorage key the legacy services/api.ts used, kept for continuity. */
export const ACCESS_TOKEN_STORAGE_KEY = 'access_token';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export const http = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

interface HttpValidationErrorBody {
  detail: { loc: (string | number)[]; msg: string; type: string }[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  return isRecord(value) && value.success === false && typeof value.error_code === 'string';
}

function isHttpValidationError(value: unknown): value is HttpValidationErrorBody {
  return isRecord(value) && Array.isArray(value.detail);
}

function asErrorCode(value: string): ErrorCode {
  return (Object.values(ErrorCode) as string[]).includes(value)
    ? (value as ErrorCode)
    : ErrorCode.UNKNOWN_ERROR;
}

/**
 * Response interceptor is written to work against BOTH shapes the backend
 * can return today: raw payloads on most /api/v1/* endpoints, and the
 * {success, data, message} envelope (currently only /mcp/v1/*, out of scope,
 * but this makes a future REST migration to the same envelope a no-op here).
 */
http.interceptors.response.use(
  (response) => {
    const body: unknown = response.data;
    if (isRecord(body) && typeof body.success === 'boolean') {
      if (body.success === false) {
        const errData = body as unknown as ApiErrorResponse;
        throw new ApiError(
          asErrorCode(errData.error_code),
          errData.message ?? 'Request failed',
          response.status
        );
      }
      return { ...response, data: body.data };
    }
    return response;
  },
  (error: AxiosError) => {
    const status = error.response?.status ?? null;
    const data: unknown = error.response?.data;

    if (isApiErrorResponse(data)) {
      return Promise.reject(
        new ApiError(asErrorCode(data.error_code), data.message ?? 'Request failed', status)
      );
    }

    if (isHttpValidationError(data)) {
      const fieldErrors: Record<string, string> = {};
      for (const item of data.detail) {
        const field = item.loc.at(-1);
        if (typeof field === 'string') {
          fieldErrors[field] = item.msg;
        }
      }
      const message = data.detail[0]?.msg ?? 'Validation error';
      return Promise.reject(
        new ApiError(ErrorCode.VALIDATION_ERROR_DETAIL, message, status, fieldErrors)
      );
    }

    if (status === 401) {
      localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(
        new ApiError(ErrorCode.UNAUTHORIZED_ERROR, 'Session expired, please log in again.', status)
      );
    }

    const message =
      (isRecord(data) && typeof data.message === 'string' ? data.message : null) ??
      error.message ??
      'Request failed';

    return Promise.reject(new ApiError(ErrorCode.UNKNOWN_ERROR, message, status));
  }
);
