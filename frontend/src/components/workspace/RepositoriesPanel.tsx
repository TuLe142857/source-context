import { useState } from 'react';
import { toast } from 'sonner';
import { Plus, Settings, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RepositoryItem } from './RepositoryItem';
import { AddRepositoryDialog } from './AddRepositoryDialog';
import type { RepositoryResponse } from '@/api/types/repository';
import type { WorkspaceResponse } from '@/api/types/workspace';
import { createGitHubInstallStateApi } from '@/api/workspaces.api';
import { getErrorMessage } from '@/lib/errors';

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
    </svg>
  );
}

export function RepositoriesPanel({
  workspace,
  repositories,
}: {
  workspace: WorkspaceResponse;
  repositories: RepositoryResponse[];
}) {
  const [addOpen, setAddOpen] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const githubAppName = import.meta.env.VITE_GITHUB_APP_NAME || 'source-context-mcp';
  const isConnected = !!workspace.github_installation_id;

  const handleConnectApp = async () => {
    const installWindow = window.open('about:blank', '_blank');
    if (!installWindow) {
      toast.error('Trình duyệt đã chặn cửa sổ cài đặt GitHub. Hãy cho phép popup rồi thử lại.');
      return;
    }

    setConnecting(true);
    try {
      const { state } = await createGitHubInstallStateApi(workspace.id);
      installWindow.location.href = `https://github.com/apps/${githubAppName}/installations/new?state=${encodeURIComponent(state)}`;
    } catch (error) {
      installWindow.close();
      toast.error(getErrorMessage(error));
    } finally {
      setConnecting(false);
    }
  };

  const handleManageApp = () => {
    if (workspace.github_installation_id) {
      const manageUrl = `https://github.com/settings/installations/${workspace.github_installation_id}`;
      window.open(manageUrl, '_blank');
    }
  };

  return (
    <div className="space-y-6">
      {/* GitHub App Integration Card */}
      <div className="glass-panel rounded-2xl p-6 border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-muted/20">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-muted rounded-xl border flex items-center justify-center">
            <GithubIcon className="w-6 h-6 text-foreground" />
          </div>
          <div>
            <h4 className="font-semibold text-foreground flex items-center gap-2">
              GitHub App Integration
              {isConnected && (
                <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-medium">
                  <CheckCircle2 className="w-3 h-3" /> Đã kết nối
                </span>
              )}
            </h4>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl font-normal leading-relaxed">
              {isConnected
                ? `Workspace này đã được liên kết với GitHub App (ID: ${workspace.github_installation_id}). Bất kỳ repository mới nào bạn thêm vào App trên GitHub sẽ tự động được theo dõi và index.`
                : 'Kết nối workspace này với GitHub App để tự động hóa việc theo dõi (track) và quét mã nguồn mỗi khi bạn thêm repository mới trên GitHub.'}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 gap-3 w-full md:w-auto">
          {isConnected ? (
            <Button variant="outline" size="sm" className="w-full md:w-auto gap-2" onClick={handleManageApp}>
              <Settings className="w-4 h-4" /> Quản lý quyền
            </Button>
          ) : (
            <Button size="sm" className="w-full md:w-auto gap-2" onClick={handleConnectApp} disabled={connecting}>
              <GithubIcon className="w-4 h-4" /> {connecting ? 'Đang kết nối…' : 'Cài đặt & Kết nối'}
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-foreground">Git Repositories ({repositories.length})</h3>
        <Button size="sm" onClick={() => setAddOpen(true)} className="gap-2">
          <Plus className="w-4 h-4" /> Thêm repository
        </Button>
      </div>

      {repositories.length > 0 ? (
        <div className="space-y-4">
          {repositories.map((repo) => (
            <RepositoryItem key={repo.id} workspaceId={workspace.id} repository={repo} />
          ))}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-10 text-center border">
          <p className="text-sm text-muted-foreground">
            Chưa có repository nào. Kết nối GitHub App hoặc thêm repository thủ công ở trên để bắt đầu cấu hình branch & sub-project.
          </p>
        </div>
      )}

      <AddRepositoryDialog workspaceId={workspace.id} open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
}
