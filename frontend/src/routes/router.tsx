import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage';
import { ResetPasswordPage } from '@/pages/ResetPasswordPage';
import { WorkspaceListPage } from '@/pages/WorkspaceListPage';
import { WorkspaceDetailPage } from '@/pages/WorkspaceDetailPage';
import { TokensPage } from '@/pages/TokensPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { SecurityPage } from '@/pages/SecurityPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/workspaces" replace /> },
          { path: 'workspaces', element: <WorkspaceListPage /> },
          { path: 'workspaces/:workspaceId', element: <WorkspaceDetailPage /> },
          { path: 'settings/tokens', element: <TokensPage /> },
          { path: 'settings/profile', element: <ProfilePage /> },
          { path: 'settings/security', element: <SecurityPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
