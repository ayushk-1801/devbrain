import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import LandingPage from './components/LandingPage';
import GraphVisualize from './components/GraphVisualize';
import DocsPage from './components/DocsPage';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import NewInstance from './components/NewInstance';
import ProtectedRoute from './components/ProtectedRoute';

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/visualize', element: <GraphVisualize /> },
  {
    path: '/docs/*',
    element: <DocsPage />,
  },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },
  {
    path: '/new-instance',
    element: (
      <ProtectedRoute>
        <NewInstance />
      </ProtectedRoute>
    ),
  },
]);

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
