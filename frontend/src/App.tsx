import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import GraphVisualize from './components/GraphVisualize';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/visualize" element={<GraphVisualize />} />
      </Routes>
    </BrowserRouter>
  );
}
