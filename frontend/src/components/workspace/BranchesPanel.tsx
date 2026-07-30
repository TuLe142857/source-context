import { useState } from 'react';
import { BranchItem } from './BranchItem';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useWorkspaceBranchesQuery } from '@/hooks/useBranches';
import type { RepositoryResponse } from '@/api/types/repository';

const ALL_REPOSITORIES = 'all';

/** Flat, workspace-scoped branch list (GET /branches/{workspaceId}/workspace-branches), filterable by repository. */
export function BranchesPanel({
  workspaceId,
  repositories,
}: {
  workspaceId: number;
  repositories: RepositoryResponse[];
}) {
  const [repositoryFilter, setRepositoryFilter] = useState<string>(ALL_REPOSITORIES);
  const repositoryId = repositoryFilter === ALL_REPOSITORIES ? undefined : Number(repositoryFilter);
  const branchesQuery = useWorkspaceBranchesQuery(workspaceId, repositoryId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h3 className="font-semibold text-foreground">Branches</h3>
        <Select value={repositoryFilter} onValueChange={setRepositoryFilter}>
          <SelectTrigger className="w-56">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_REPOSITORIES}>Tất cả repository</SelectItem>
            {repositories.map((repo) => (
              <SelectItem key={repo.id} value={String(repo.id)}>
                {repo.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {branchesQuery.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : branchesQuery.data && branchesQuery.data.length > 0 ? (
        <div className="space-y-2">
          {branchesQuery.data.map((branch) => (
            <BranchItem key={branch.id} workspaceId={workspaceId} branch={branch} />
          ))}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-10 text-center border">
          <p className="text-sm text-muted-foreground">Không có branch nào khớp bộ lọc.</p>
        </div>
      )}
    </div>
  );
}
