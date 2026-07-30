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
import { useUpdateProjectMutation } from '@/hooks/useProjects';
import { SOURCE_LANGUAGES, type ProjectResponse, type SourceLanguage } from '@/api/types/project';
import { getErrorMessage } from '@/lib/errors';

interface EditProjectDialogProps {
  workspaceId: number;
  project: ProjectResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditProjectDialog({ workspaceId, project, open, onOpenChange }: EditProjectDialogProps) {
  const updateMutation = useUpdateProjectMutation(workspaceId);
  const [rootDir, setRootDir] = useState(project.root_dir);
  const [language, setLanguage] = useState<SourceLanguage>(project.language);

  const handleOpenChange = (next: boolean) => {
    if (next) {
      setRootDir(project.root_dir);
      setLanguage(project.language);
    }
    onOpenChange(next);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(
      { projectId: project.id, data: { root_dir: rootDir, language } },
      {
        onSuccess: () => {
          toast.success('Đã cập nhật sub-project.');
          onOpenChange(false);
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Sửa sub-project</DialogTitle>
            <DialogDescription>Cập nhật thư mục con và/hoặc ngôn ngữ chính.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor={`edit-root-dir-${project.id}`}>Root dir</Label>
              <Input
                id={`edit-root-dir-${project.id}`}
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
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Lưu thay đổi'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
