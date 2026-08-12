import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import GuestGenerationPage from './pages/GuestGenerationPage';
import StudioPage from './pages/StudioPage';

export default function App() {
  return (
    <div className="min-h-screen bg-studio-bg">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/generate" element={<GuestGenerationPage />} />
        <Route path="/studio/:discussionId" element={<StudioPage />} />
      </Routes>
    </div>
  );
}
