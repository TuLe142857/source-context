import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getMeApi, loginApi, registerApi } from '@/api/auth.api';
import type { UserLoginRequest, UserRegisterRequest } from '@/api/types/auth';
import { logout as logoutAction, setCredentials, setUser } from '@/store/authSlice';
import { useAppDispatch, useAppSelector } from '@/store/hooks';

export function useSession() {
  return useAppSelector((state) => state.auth);
}

/** Hydrates/validates the session on app bootstrap when a token is already present. */
export function useCurrentUserQuery() {
  const dispatch = useAppDispatch();
  const token = useAppSelector((state) => state.auth.token);

  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const user = await getMeApi();
      dispatch(setUser(user));
      return user;
    },
    enabled: Boolean(token),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLoginMutation() {
  const dispatch = useAppDispatch();
  return useMutation({
    mutationFn: (data: UserLoginRequest) => loginApi(data),
    onSuccess: (res) => {
      dispatch(setCredentials({ user: res.user, token: res.access_token }));
    },
  });
}

export function useRegisterMutation() {
  const dispatch = useAppDispatch();
  return useMutation({
    mutationFn: (data: UserRegisterRequest) => registerApi(data),
    onSuccess: (res) => {
      dispatch(setCredentials({ user: res.user, token: res.access_token }));
    },
  });
}

export function useLogout() {
  const dispatch = useAppDispatch();
  const queryClient = useQueryClient();
  return () => {
    dispatch(logoutAction());
    queryClient.clear();
  };
}
