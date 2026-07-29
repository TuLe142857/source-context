import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Copy, KeyRound, Loader2, Plus, ShieldAlert, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { useCreatePatMutation, usePatsQuery, useRevokePatMutation } from '@/hooks/useTokens';
import type { PATCreateResponse, PATResponse } from '@/api/types/tokens';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage } from '@/lib/errors';

export function TokensPage() {
  const patsQuery = usePatsQuery();
  const createMutation = useCreatePatMutation();
  const revokeMutation = useRevokePatMutation();

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [expiresInDays, setExpiresInDays] = useState('365');
  const [createdToken, setCreatedToken] = useState<PATCreateResponse | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<PATResponse | null>(null);

  const handleCreate = (e: FormEvent) => {
    e.preventDefault();
    createMutation.mutate(
      { name, expires_in_days: expiresInDays ? Number(expiresInDays) : null },
      {
        onSuccess: (res) => {
          setCreateOpen(false);
          setName('');
          setExpiresInDays('365');
          setCreatedToken(res);
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  const handleRevoke = () => {
    if (!revokeTarget) return;
    revokeMutation.mutate(revokeTarget.id, {
      onSuccess: () => {
        toast.success(`Đã thu hồi token "${revokeTarget.name}".`);
        setRevokeTarget(null);
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  const copyToken = async (token: string) => {
    await navigator.clipboard.writeText(token);
    toast.success('Đã copy token vào clipboard.');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <KeyRound className="w-6 h-6 text-primary" /> Personal Access Tokens
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Dùng cho các client bên ngoài (vd. MCP CLI) xác thực với API bằng Bearer token.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="w-4 h-4" /> Tạo API Key
        </Button>
      </div>

      <div className="glass-card rounded-2xl border overflow-hidden">
        {patsQuery.isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : patsQuery.data && patsQuery.data.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tên</TableHead>
                <TableHead>Prefix</TableHead>
                <TableHead>Dùng lần cuối</TableHead>
                <TableHead>Hết hạn</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead className="text-right">Hành động</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {patsQuery.data.map((pat) => (
                <TableRow key={pat.id}>
                  <TableCell className="font-medium">{pat.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {pat.token_prefix}…
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(pat.last_used_at)}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(pat.expires_at)}</TableCell>
                  <TableCell>
                    {pat.is_revoked ? (
                      <Badge variant="destructive">Đã thu hồi</Badge>
                    ) : (
                      <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                        Hoạt động
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      disabled={pat.is_revoked}
                      onClick={() => setRevokeTarget(pat)}
                      title="Thu hồi token"
                    >
                      <Trash2 className="w-4 h-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="p-10 text-center text-sm text-muted-foreground">
            Chưa có API key nào. Tạo một key để dùng với MCP CLI hoặc các client bên ngoài.
          </div>
        )}
      </div>

      {/* Create PAT dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle>Tạo Personal Access Token</DialogTitle>
              <DialogDescription>
                Token sẽ chỉ hiển thị đầy đủ MỘT LẦN ngay sau khi tạo — hãy lưu lại ngay.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-1.5">
                <Label htmlFor="pat-name">Tên token</Label>
                <Input
                  id="pat-name"
                  required
                  placeholder="My Macbook CLI"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pat-expires">Hết hạn sau (ngày)</Label>
                <Input
                  id="pat-expires"
                  type="number"
                  min={1}
                  value={expiresInDays}
                  onChange={(e) => setExpiresInDays(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Tạo token'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* One-time raw token reveal */}
      <Dialog open={!!createdToken} onOpenChange={(open) => !open && setCreatedToken(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" /> Token đã tạo thành công
            </DialogTitle>
            <DialogDescription>
              Đây là lần DUY NHẤT bạn thấy token đầy đủ. Hãy copy và lưu trữ an toàn ngay bây giờ.
            </DialogDescription>
          </DialogHeader>
          {createdToken && (
            <div className="flex items-center gap-2 bg-muted rounded-xl p-3 font-mono text-xs break-all">
              <span className="flex-1">{createdToken.raw_token}</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => copyToken(createdToken.raw_token)}
              >
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setCreatedToken(null)}>Đã lưu, đóng lại</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke confirm */}
      <AlertDialog open={!!revokeTarget} onOpenChange={(open) => !open && setRevokeTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Thu hồi token "{revokeTarget?.name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              Mọi client đang dùng token này sẽ mất quyền truy cập ngay lập tức. Hành động này không thể
              hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction onClick={handleRevoke} disabled={revokeMutation.isPending}>
              Thu hồi
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
