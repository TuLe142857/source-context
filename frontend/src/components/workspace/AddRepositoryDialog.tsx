import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useCreateRepositoryMutation, useInspectBranchesMutation } from '@/hooks/useRepositories';
import type { RemoteBranchesResponse } from '@/api/types/repository';
import { getErrorMessage } from '@/lib/errors';

interface AddRepositoryDialogProps {
  workspaceId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddRepositoryDialog({ workspaceId, open, onOpenChange }: AddRepositoryDialogProps) {
  const inspectMutation = useInspectBranchesMutation();
  const createMutation = useCreateRepositoryMutation(workspaceId);

  const [name, setName] = useState('');
  const [gitUrl, setGitUrl] = useState('');
  const [inspectResult, setInspectResult] = useState<RemoteBranchesResponse | null>(null);
  const [selectedBranches, setSelectedBranches] = useState<Set<string>>(new Set());

  const reset = () => {
    setName('');
    setGitUrl('');
    setInspectResult(null);
    setSelectedBranches(new Set());
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const handleInspect = (e: FormEvent) => {
    e.preventDefault();
    inspectMutation.mutate(
      { workspaceId, data: { git_url: gitUrl } },
      {
        onSuccess: (res) => {
          setInspectResult(res);
          setSelectedBranches(new Set(res.branches.includes('main') ? ['main'] : res.branches.slice(0, 1)));
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  const toggleBranch = (branchName: string) => {
    setSelectedBranches((prev) => {
      const next = new Set(prev);
      if (next.has(branchName)) next.delete(branchName);
      else next.add(branchName);
      return next;
    });
  };

  const handleCreate = () => {
    if (selectedBranches.size === 0) {
      toast.error('Chọn ít nhất một branch để đăng ký.');
      return;
    }
    createMutation.mutate(
      {
        name,
        git_url: gitUrl,
        branches: Array.from(selectedBranches).map((branch_name) => ({
          branch_name,
          commit_hashed: 'HEAD',
        })),
      },
      {
        onSuccess: () => {
          toast.success(`Đã thêm repository "${name}".`);
          handleOpenChange(false);
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        {!inspectResult ? (
          <form onSubmit={handleInspect}>
            <DialogHeader>
              <DialogTitle>Thêm Git Repository — Bước 1/2</DialogTitle>
              <DialogDescription>Nhập URL để xem các branch khả dụng trên remote.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-1.5">
                <Label htmlFor="repo-name">Tên repository</Label>
                <Input
                  id="repo-name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="my-service"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="repo-git-url">Git URL</Label>
                <Input
                  id="repo-git-url"
                  required
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo.git"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={inspectMutation.isPending}>
                {inspectMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Xem branches'}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Thêm Git Repository — Bước 2/2</DialogTitle>
              <DialogDescription>
                Chọn các branch cần đăng ký cho "{inspectResult.owner}/{inspectResult.repo_name}".
              </DialogDescription>
            </DialogHeader>
            <div className="py-4 space-y-2 max-h-64 overflow-y-auto">
              {inspectResult.branches.map((branch) => (
                <label
                  key={branch}
                  className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm cursor-pointer hover:bg-muted/60"
                >
                  <input
                    type="checkbox"
                    checked={selectedBranches.has(branch)}
                    onChange={() => toggleBranch(branch)}
                    className="accent-primary"
                  />
                  <span className="font-mono">{branch}</span>
                </label>
              ))}
            </div>
            <DialogFooter className="sm:justify-between">
              <Button type="button" variant="ghost" onClick={() => setInspectResult(null)}>
                <ArrowLeft className="w-4 h-4" /> Quay lại
              </Button>
              <Button type="button" onClick={handleCreate} disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  `Đăng ký ${selectedBranches.size} branch`
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
