import { useMutation } from '@tanstack/react-query';
import {
  changePasswordApi,
  forgotPasswordApi,
  resetPasswordApi,
  updateProfileApi,
} from '@/api/account.template';

/** All template only — none of these endpoints exist on the backend yet. */
export function useChangePasswordMutation() {
  return useMutation({ mutationFn: changePasswordApi });
}

export function useForgotPasswordMutation() {
  return useMutation({ mutationFn: forgotPasswordApi });
}

export function useResetPasswordMutation() {
  return useMutation({ mutationFn: resetPasswordApi });
}

export function useUpdateProfileMutation() {
  return useMutation({ mutationFn: updateProfileApi });
}
