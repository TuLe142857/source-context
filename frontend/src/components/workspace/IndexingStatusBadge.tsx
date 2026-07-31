import { Badge } from '@/components/ui/badge';
import type { BranchIndexingStatus } from '@/api/types/branch';

const STATUS_STYLES: Record<BranchIndexingStatus, string> = {
  UNINDEXED: 'bg-muted text-muted-foreground border-border',
  INDEXING: 'bg-sky-500/15 text-sky-400 border-sky-500/30 animate-pulse',
  INDEXED: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  OUTDATED: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  FAILED: 'bg-destructive/15 text-destructive border-destructive/30',
};

const STATUS_LABELS: Record<BranchIndexingStatus, string> = {
  UNINDEXED: 'Chưa index',
  INDEXING: 'Đang index',
  INDEXED: 'Đã index',
  OUTDATED: 'Cần index lại',
  FAILED: 'Lỗi index',
};

export function IndexingStatusBadge({ status }: { status: BranchIndexingStatus }) {
  return <Badge className={STATUS_STYLES[status]}>{STATUS_LABELS[status]}</Badge>;
}
