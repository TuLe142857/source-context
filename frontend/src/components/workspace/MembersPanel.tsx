import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Crown, Loader2, LogOut, Plus, Trash2, UserRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { TemplateBadge } from '@/components/TemplateBadge';
import { useAddMemberMutation, useLeaveWorkspaceMutation, useRemoveMemberMutation } from '@/hooks/useWorkspaces';
import { useSession } from '@/hooks/useAuth';
import type { MemberResponse } from '@/api/types/workspace';
import { getErrorMessage } from '@/lib/errors';

export function MembersPanel({
  workspaceId,
  ownerId,
  members,
}: {
  workspaceId: number;
  ownerId: number;
  members: MemberResponse[];
}) {
  const { user } = useSession();
  const addMutation = useAddMemberMutation(workspaceId);
  const removeMutation = useRemoveMemberMutation(workspaceId);
  const leaveMutation = useLeaveWorkspaceMutation();

  const [email, setEmail] = useState('');
  const [removeTarget, setRemoveTarget] = useState<MemberResponse | null>(null);
  const [leaveOpen, setLeaveOpen] = useState(false);

  const handleAdd = (e: FormEvent) => {
    e.preventDefault();
    addMutation.mutate(
      { email },
      {
        onSuccess: () => {
          toast.success(`Đã thêm thành viên "${email}".`);
          setEmail('');
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  const handleRemove = () => {
    if (!removeTarget) return;
    const label = removeTarget.username ?? removeTarget.email ?? `#${removeTarget.user_id}`;
    removeMutation.mutate(removeTarget.user_id, {
      onSuccess: () => toast.success(`Đã xoá "${label}" khỏi workspace.`),
      onError: (err) => toast.error(getErrorMessage(err)),
      onSettled: () => setRemoveTarget(null),
    });
  };

  const handleLeave = () => {
    leaveMutation.mutate(workspaceId, {
      onError: (err) => toast.error(getErrorMessage(err)),
      onSettled: () => setLeaveOpen(false),
    });
  };

  const isOwner = user?.id === ownerId;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-foreground">Thành viên workspace</h3>
        {!isOwner && (
          <Button variant="outline" size="sm" onClick={() => setLeaveOpen(true)}>
            <LogOut className="w-3.5 h-3.5" /> Rời workspace <TemplateBadge />
          </Button>
        )}
      </div>

      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <Input
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Button type="submit" disabled={addMutation.isPending}>
          {addMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Thêm
        </Button>
      </form>

      <div className="space-y-2">
        {members.map((member) => {
          const memberIsOwner = member.user_id === ownerId;
          return (
            <div
              key={member.user_id}
              className="flex items-center justify-between gap-3 rounded-xl border border-border bg-background/40 px-3 py-2"
            >
              <div className="flex items-center gap-2 min-w-0">
                <UserRound className="w-4 h-4 text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm text-foreground truncate">
                    {member.full_name ?? member.username ?? member.email ?? `#${member.user_id}`}
                  </p>
                  {member.email && <p className="text-xs text-muted-foreground truncate">{member.email}</p>}
                </div>
                {memberIsOwner && (
                  <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 gap-1">
                    <Crown className="w-3 h-3" /> Owner
                  </Badge>
                )}
              </div>
              {!memberIsOwner && (
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    title="Xoá thành viên"
                    onClick={() => setRemoveTarget(member)}
                  >
                    <Trash2 className="w-3.5 h-3.5 text-destructive" />
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <AlertDialog open={!!removeTarget} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá thành viên này khỏi workspace?</AlertDialogTitle>
            <AlertDialogDescription>Hành động này không thể hoàn tác.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction onClick={handleRemove} disabled={removeMutation.isPending}>
              Xoá
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={leaveOpen} onOpenChange={setLeaveOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rời khỏi workspace này?</AlertDialogTitle>
            <AlertDialogDescription>
              Tính năng này chưa được backend hỗ trợ — đây là giao diện chuẩn bị trước.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction onClick={handleLeave}>Rời workspace</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
