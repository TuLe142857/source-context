import React from 'react';
import { useAuth } from '../context/AuthContext';
import { FolderGit2, LogOut, Sparkles } from 'lucide-react';

interface NavbarProps {
  onGoHome: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onGoHome }) => {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div 
          onClick={onGoHome}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/30 group-hover:scale-105 transition-transform duration-200">
            <FolderGit2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-white tracking-tight">SourceContext</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> v1.0
              </span>
            </div>
            <p className="text-xs text-gray-400 hidden sm:block">Repository & Code Knowledge Hub</p>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-xl bg-slate-800/60 border border-white/10">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-400/30 flex items-center justify-center text-indigo-300 font-bold text-sm">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-xs font-semibold text-white leading-tight">{user.full_name || user.username}</p>
                <p className="text-[11px] text-gray-400">{user.email}</p>
              </div>
            </div>

            <button
              onClick={logout}
              className="p-2.5 rounded-xl bg-slate-800/80 text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 border border-white/10 hover:border-rose-500/30 transition-all flex items-center gap-2 text-xs font-medium"
              title="Đăng xuất"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Đăng xuất</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
