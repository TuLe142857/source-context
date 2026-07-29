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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useCreateProjectMutation } from '@/hooks/useProjects';
import { SOURCE_LANGUAGES, type SourceLanguage } from '@/api/types/project';
import { getErrorMessage } from '@/lib/errors';

interface AddProjectDialogProps {
  workspaceId: number;
  branchId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddProjectDialog({ workspaceId, branchId, open, onOpenChange }: AddProjectDialogProps) {
  const createMutation = useCreateProjectMutation(workspaceId);
  const [rootDir, setRootDir] = useState('.');
  const [language, setLanguage] = useState<SourceLanguage>('python');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    createMutation.mutate(
      { branchId, data: { root_dir: rootDir, language } },
      {
        onSuccess: () => {
          toast.success('Đã thêm sub-project.');
          onOpenChange(false);
          setRootDir('.');
          setLanguage('python');
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Thêm sub-project (SCIP target)</DialogTitle>
            <DialogDescription>
              Chỉ định thư mục con và ngôn ngữ chính để pipeline lập chỉ mục xử lý.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="root-dir">Root dir</Label>
              <Input
                id="root-dir"
                required
                value={rootDir}
                onChange={(e) => setRootDir(e.target.value)}
                placeholder="., backend/, apps/api"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Ngôn ngữ</Label>
              <Select value={language} onValueChange={(v) => setLanguage(v as SourceLanguage)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_LANGUAGES.map((lang) => (
                    <SelectItem key={lang} value={lang}>
                      {lang}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Thêm sub-project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
