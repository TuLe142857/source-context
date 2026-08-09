import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { WorkspaceListPage } from '@/pages/WorkspaceListPage';
import { WorkspaceDetailPage } from '@/pages/WorkspaceDetailPage';
import { TokensPage } from '@/pages/TokensPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
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
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
