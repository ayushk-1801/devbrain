import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import LandingPage from './components/LandingPage';
import GraphVisualize from './components/GraphVisualize';
import DocsPage from './components/DocsPage';

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/visualize', element: <GraphVisualize /> },
  {
    path: '/docs/*',
    element: <DocsPage />,
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
