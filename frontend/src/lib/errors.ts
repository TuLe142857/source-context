import { ApiError } from '@/api/types/common';
import { TemplateNotImplementedError } from '@/api/template';

export function getErrorMessage(error: unknown, fallback = 'Đã có lỗi xảy ra. Vui lòng thử lại.'): string {
  if (error instanceof ApiError || error instanceof TemplateNotImplementedError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
