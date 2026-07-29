import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createPatApi, listPatsApi, revokePatApi } from '@/api/tokens.api';
import type { PATCreateRequest } from '@/api/types/tokens';

const TOKENS_KEY = ['tokens'] as const;

export function usePatsQuery() {
  return useQuery({ queryKey: TOKENS_KEY, queryFn: listPatsApi });
}

export function useCreatePatMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PATCreateRequest) => createPatApi(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TOKENS_KEY });
    },
  });
}

export function useRevokePatMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tokenId: number) => revokePatApi(tokenId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TOKENS_KEY });
    },
  });
}
