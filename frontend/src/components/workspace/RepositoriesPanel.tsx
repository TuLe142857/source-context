import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RepositoryItem } from './RepositoryItem';
import { AddRepositoryDialog } from './AddRepositoryDialog';
import type { RepositoryResponse } from '@/api/types/repository';

export function RepositoriesPanel({
  workspaceId,
  repositories,
}: {
  workspaceId: number;
  repositories: RepositoryResponse[];
}) {
  const [addOpen, setAddOpen] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-foreground">Git Repositories</h3>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus className="w-4 h-4" /> Thêm repository
        </Button>
      </div>

      {repositories.length > 0 ? (
        <div className="space-y-4">
          {repositories.map((repo) => (
            <RepositoryItem key={repo.id} workspaceId={workspaceId} repository={repo} />
          ))}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-10 text-center border">
          <p className="text-sm text-muted-foreground">
            Chưa có repository nào. Thêm repository để bắt đầu cấu hình branch & sub-project.
          </p>
        </div>
      )}

      <AddRepositoryDialog workspaceId={workspaceId} open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
}
