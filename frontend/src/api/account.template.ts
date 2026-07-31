import { notImplemented } from './template';
import type { UserResponse } from './types/auth';
import type {
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
} from './types/templates';

/** No change-password endpoint exists in the backend spec yet. */
export function changePasswordApi(_data: ChangePasswordRequest): Promise<void> {
  return notImplemented('Đổi mật khẩu');
}

/** No forgot-password endpoint exists in the backend spec yet. */
export function forgotPasswordApi(_data: ForgotPasswordRequest): Promise<void> {
  return notImplemented('Quên mật khẩu');
}

/** No reset-password endpoint exists in the backend spec yet. */
export function resetPasswordApi(_data: ResetPasswordRequest): Promise<void> {
  return notImplemented('Đặt lại mật khẩu');
}

/** No update-own-profile endpoint exists in the backend spec yet (only register/login/me read). */
export function updateProfileApi(_data: UpdateProfileRequest): Promise<UserResponse> {
  return notImplemented('Cập nhật hồ sơ cá nhân');
}
