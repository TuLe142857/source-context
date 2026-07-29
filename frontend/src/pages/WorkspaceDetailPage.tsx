import { useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { OverviewPanel } from '@/components/workspace/OverviewPanel';
import { MembersPanel } from '@/components/workspace/MembersPanel';
import { RepositoriesPanel } from '@/components/workspace/RepositoriesPanel';
import { IndexingPanel } from '@/components/workspace/IndexingPanel';
import { useWorkspaceHierarchyQuery, useWorkspaceQuery } from '@/hooks/useWorkspaces';

export function WorkspaceDetailPage() {
  const params = useParams<{ workspaceId: string }>();
  const workspaceId = Number(params.workspaceId);

  const workspaceQuery = useWorkspaceQuery(workspaceId);
  const hierarchyQuery = useWorkspaceHierarchyQuery(workspaceId);

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{workspace.workspace_name}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {hierarchy.repositories.length} repositories · {hierarchy.members.length} thành viên
        </p>
      </div>

      <Tabs defaultValue="repositories">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="members">Thành viên</TabsTrigger>
          <TabsTrigger value="repositories">Repositories</TabsTrigger>
          <TabsTrigger value="indexing">Indexing</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewPanel workspace={workspace} />
        </TabsContent>

        <TabsContent value="members">
          <MembersPanel workspaceId={workspaceId} ownerId={hierarchy.owner_id} members={hierarchy.members} />
        </TabsContent>

        <TabsContent value="repositories">
          <RepositoriesPanel workspaceId={workspaceId} repositories={hierarchy.repositories} />
        </TabsContent>

        <TabsContent value="indexing">
          <IndexingPanel workspaceId={workspaceId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
