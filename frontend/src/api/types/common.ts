/**
 * Mirrors backend/app/core/response.py and backend/app/core/error_code.py.
 *
 * Only the /mcp/v1/* surface (out of scope for this app) uses this envelope
 * today — the /api/v1/* REST endpoints this app calls still return raw
 * payloads. These types exist so that when the backend migrates a REST
 * endpoint to the unified envelope, `src/api/http.ts` can adapt transparently
 * without any change to callers.
 */

export interface PaginationMeta {
  current_page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  message: string | null;
}

export interface ApiPaginationResponse<T> {
  success: true;
  data: T[];
  message: string | null;
  meta: PaginationMeta;
}

export interface ApiErrorResponse {
  success: false;
  error_code: string;
  message: string | null;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

/**
 * Mirrors ErrorCode.error_code string values in backend/app/core/error_code.py
 * exactly. Written as a const object + derived union (not a TS `enum`) since
 * this project's tsconfig enables `erasableSyntaxOnly`.
 */
export const ErrorCode = {
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
  SYSTEM_ERROR: 'SYSTEM_ERROR',
  UNAUTHORIZED_ERROR: 'UNAUTHORIZED_ERROR',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  JWT_TOKEN_REVOKED: 'JWT_TOKEN_REVOKED',
  JWT_TOKEN_EXPIRED: 'JWT_TOKEN_EXPIRED',
  JWT_TOKEN_NOT_FRESH: 'JWT_TOKEN_NOT_FRESH',
  INVALID_JWT_TOKEN: 'INVALID_JWT_TOKEN',
  LOGIN_FAILED: 'LOGIN_FAILED',
  FORBIDDEN: 'FORBIDDEN',
  USER_NOT_ACTIVE: 'USER_NOT_ACTIVE',
  BAD_REQUEST: 'BAD_REQUEST',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_CODE: 'INVALID_CODE',
  CODE_EXPIRED: 'CODE_EXPIRED',
  ACTION_ALREADY_PERFORMED: 'ACTION_ALREADY_PERFORMED',
  ACTION_CONFLICT: 'ACTION_CONFLICT',
  RESOURCE_NOT_FOUND: 'RESOURCE_NOT_FOUND',
  RESOURCE_ALREADY_EXISTS: 'RESOURCE_ALREADY_EXISTS',
  RESOURCE_CONFLICT: 'RESOURCE_CONFLICT',
  RESOURCE_NOT_AVAILABLE: 'RESOURCE_NOT_AVAILABLE',
  RESOURCE_IN_USE: 'RESOURCE_IN_USE',
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',
  DATA_INTEGRITY_ERROR: 'DATA_INTEGRITY_ERROR',
  FILE_TOO_LARGE: 'FILE_TOO_LARGE',
  UNSUPPORTED_FILE_TYPE: 'UNSUPPORTED_FILE_TYPE',
  FILE_UPLOAD_FAILED: 'FILE_UPLOAD_FAILED',
  /** Client-side only: FastAPI's default HTTPValidationError shape, not a backend ErrorCode. */
  VALIDATION_ERROR_DETAIL: 'VALIDATION_ERROR_DETAIL',
} as const;

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode];

/** One entry of FastAPI's default `HTTPValidationError.detail[]`. */
export interface ValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/**
 * Normalized error thrown by the axios response interceptor for every
 * failed request, regardless of whether the backend responded with the
 * legacy raw-`detail` validation shape or the unified error envelope.
 */
export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number | null;
  readonly fieldErrors?: Record<string, string>;

  constructor(
    code: ErrorCode,
    message: string,
    status: number | null = null,
    fieldErrors?: Record<string, string>
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}
