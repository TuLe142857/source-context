import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { BookOpen, Check, Copy, KeyRound, Loader2, Plus, ShieldAlert, Trash2 } from 'lucide-react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { useCreatePatMutation, usePatsQuery, useRevokePatMutation } from '@/hooks/useTokens';
import type { PATCreateResponse, PATResponse } from '@/api/types/tokens';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage } from '@/lib/errors';

const ANTIGRAVITY_MCP_CONFIG = `{
    "mcpServers": {
        "source-context-mcp": {
            "command": "uvx",
            "args": [
                "source-context-mcp",
                "run"
            ]
        }
    }
}`;

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="relative group">
      <pre className="bg-muted rounded-xl p-3 pr-10 font-mono text-xs overflow-x-auto">
        <code>{code}</code>
      </pre>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute top-1.5 right-1.5 h-7 w-7"
        onClick={handleCopy}
        title="Copy"
      >
        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      </Button>
    </div>
  );
}

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

      <div className="glass-card rounded-2xl border p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary" /> Hướng dẫn kết nối MCP Server
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Dùng token ở trên để cấu hình MCP CLI, sau đó thêm MCP server vào agent bạn đang dùng.
          </p>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-medium text-foreground">1. Cấu hình Personal Access Token</h3>
          <CodeBlock code="uvx source-context-mcp config --token <Your token>" />
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">2. Thêm MCP server vào Agent</h3>
          <Tabs defaultValue="claude-code">
            <TabsList>
              <TabsTrigger value="claude-code">Claude Code</TabsTrigger>
              <TabsTrigger value="antigravity">Antigravity (IDE &amp; CLI)</TabsTrigger>
            </TabsList>

            <TabsContent value="claude-code" className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">Thêm cho thư mục làm việc hiện tại:</p>
                <CodeBlock code="claude mcp add --scope project source-context -- uvx source-context-mcp run" />
              </div>
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">Thêm vào cấu hình toàn cục:</p>
                <CodeBlock code="claude mcp add --scope user source-context -- uvx source-context-mcp run" />
              </div>
            </TabsContent>

            <TabsContent value="antigravity" className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">
                  Thêm cho thư mục làm việc hiện tại — ghi vào file{' '}
                  <code className="font-mono text-foreground">.agents/mcp_config.json</code>:
                </p>
                <CodeBlock code={ANTIGRAVITY_MCP_CONFIG} />
              </div>
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">Thêm vào cấu hình toàn cục — ghi vào file:</p>
                <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-0.5">
                  <li>
                    Linux/macOS: <code className="font-mono text-foreground">~/.gemini/config/mcp_config.json</code>
                  </li>
                  <li>
                    Windows:{' '}
                    <code className="font-mono text-foreground">
                      C:\Users\{'{username}'}\.gemini\config\mcp_config.json
                    </code>
                  </li>
                </ul>
                <CodeBlock code={ANTIGRAVITY_MCP_CONFIG} />
              </div>
            </TabsContent>
          </Tabs>
        </div>
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
