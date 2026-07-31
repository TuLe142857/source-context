import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
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
import { TemplateBadge } from '@/components/TemplateBadge';
import { useAddBranchToRepositoryMutation } from '@/hooks/useRepositories';
import { getErrorMessage } from '@/lib/errors';

interface AddBranchToRepositoryDialogProps {
  workspaceId: number;
  repositoryId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Template only — see repositories.template.ts, no such endpoint exists on the backend yet. */
export function AddBranchToRepositoryDialog({
  workspaceId,
  repositoryId,
  open,
  onOpenChange,
}: AddBranchToRepositoryDialogProps) {
  const mutation = useAddBranchToRepositoryMutation(workspaceId);
  const [branchName, setBranchName] = useState('');
  const [commitHashed, setCommitHashed] = useState('HEAD');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate(
      { repositoryId, data: { branch_name: branchName, commit_hashed: commitHashed } },
      { onError: (err) => toast.error(getErrorMessage(err)) }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Thêm branch vào repository <TemplateBadge />
            </DialogTitle>
            <DialogDescription>
              Backend hiện chỉ cho phép đăng ký branch cùng lúc tạo repository — đây là giao diện
              chuẩn bị trước cho tính năng thêm branch vào repo đã tồn tại.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="branch-name">Tên branch</Label>
              <Input
                id="branch-name"
                required
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                placeholder="develop"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="commit-hashed">Commit hash</Label>
              <Input
                id="commit-hashed"
                value={commitHashed}
                onChange={(e) => setCommitHashed(e.target.value)}
                placeholder="HEAD"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Thêm branch'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
