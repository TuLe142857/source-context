import { FlaskConical } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

/**
 * Visible marker for UI built ahead of its backend endpoint (see
 * "Missing-API Items" in plans/frontend_dev_plan.md) — the flow is fully
 * clickable, but the underlying call is a stub that always rejects.
 */
export function TemplateBadge({ label = 'Sắp có' }: { label?: string }) {
  return (
    <Badge variant="outline" className="border-amber-500/40 text-amber-400 gap-1 font-normal">
      <FlaskConical className="w-3 h-3" /> {label}
    </Badge>
  );
}
