import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import NewScreening from './pages/NewScreening';
import ScreeningResult from './pages/ScreeningResult';
import ScreeningHistory from './pages/ScreeningHistory';
import ScreeningDetails from './pages/ScreeningDetails';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="screening/new" element={<NewScreening />} />
          <Route path="screening/result/:id" element={<ScreeningResult />} />
          <Route path="screening/history" element={<ScreeningHistory />} />
          <Route path="screening/details/:id" element={<ScreeningDetails />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
