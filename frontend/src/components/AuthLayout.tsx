import type { ReactNode } from 'react';
import { FolderGit2, Sparkles } from 'lucide-react';

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 shadow-xl shadow-indigo-500/25 mb-4">
            <FolderGit2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold text-foreground tracking-tight">
            Source<span className="glow-gradient-text">Context</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-2">{subtitle}</p>
        </div>

        <div className="glass-panel rounded-3xl p-6 sm:p-8 shadow-2xl border border-white/10">
          <h2 className="text-lg font-semibold text-foreground mb-6">{title}</h2>
          {children}
        </div>

        {footer && (
          <p className="text-center text-xs text-muted-foreground mt-6 flex items-center justify-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> {footer}
          </p>
        )}
      </div>
    </div>
  );
}
