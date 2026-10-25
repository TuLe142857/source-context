import { useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { OverviewPanel } from '@/components/workspace/OverviewPanel';
import { MembersPanel } from '@/components/workspace/MembersPanel';
import { RepositoriesPanel } from '@/components/workspace/RepositoriesPanel';
import { BranchesPanel } from '@/components/workspace/BranchesPanel';
import { IndexingPanel } from '@/components/workspace/IndexingPanel';
import { linkGitHubInstallation } from '@/api/webhooks.api';
import { useWorkspaceHierarchyQuery, useWorkspaceMembersQuery, useWorkspaceQuery } from '@/hooks/useWorkspaces';

export function WorkspaceDetailPage() {
  const params = useParams<{ workspaceId: string }>();
  const workspaceId = Number(params.workspaceId);
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  useEffect(() => {
    const pendingInstallationId = searchParams.get('pending_installation_id');
    if (pendingInstallationId) {
      linkGitHubInstallation({
        installation_id: Number(pendingInstallationId),
        workspace_id: workspaceId,
      })
        .then(() => {
          toast.success('Liên kết tài khoản với GitHub App thành công!');
          queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
          queryClient.invalidateQueries({ queryKey: ['workspaces', workspaceId] });
        })
        .catch((err) => {
          toast.error('Không thể liên kết GitHub App: ' + (err?.message || 'Lỗi'));
        })
        .finally(() => {
          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              next.delete('pending_installation_id');
              next.delete('setup_action');
              return next;
            },
            { replace: true }
          );
        });
      return;
    }

    if (searchParams.get('github_connected') === 'true') {
      toast.success('Liên kết tài khoản với GitHub App thành công!');
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      queryClient.invalidateQueries({ queryKey: ['workspaces', workspaceId] });
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete('github_connected');
          return next;
        },
        { replace: true }
      );
    }
  }, [searchParams, setSearchParams, queryClient, workspaceId]);

  const workspaceQuery = useWorkspaceQuery(workspaceId);
  const hierarchyQuery = useWorkspaceHierarchyQuery(workspaceId);
  const membersQuery = useWorkspaceMembersQuery(workspaceId);

  if (workspaceQuery.isLoading || hierarchyQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!workspaceQuery.data || !hierarchyQuery.data) {
    return <p className="text-sm text-muted-foreground">Không tìm thấy workspace.</p>;
  }

  const workspace = workspaceQuery.data;
  const hierarchy = hierarchyQuery.data;
  const members = membersQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{workspace.workspace_name}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {hierarchy.repositories.length} repositories · {members.length} thành viên
        </p>
      </div>

      <Tabs defaultValue="repositories">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="members">Thành viên</TabsTrigger>
          <TabsTrigger value="repositories">Repositories</TabsTrigger>
          <TabsTrigger value="branches">Branches</TabsTrigger>
          <TabsTrigger value="indexing">Indexing</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewPanel workspace={workspace} />
        </TabsContent>

        <TabsContent value="members">
          <MembersPanel workspaceId={workspaceId} ownerId={hierarchy.owner_id} members={members} />
        </TabsContent>

        <TabsContent value="repositories">
          <RepositoriesPanel workspace={workspace} repositories={hierarchy.repositories} />
        </TabsContent>

        <TabsContent value="branches">
          <BranchesPanel workspaceId={workspaceId} repositories={hierarchy.repositories} />
        </TabsContent>

        <TabsContent value="indexing">
          <IndexingPanel workspaceId={workspaceId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
