import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './hooks/useAuth';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Upcoming from './pages/Upcoming';
import History from './pages/History';
import TodayTasks from './pages/TodayTasks';
import Pricing from './pages/Pricing';
import Payment from './pages/Payment';
import Profile from './pages/Profile';
import PremiumLab from './pages/PremiumLab';
import LoadingScreen from './components/LoadingScreen';

function Private({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="top-center"
          toastOptions={{
            style: { borderRadius: '12px', background: '#1a1a2e', color: '#fff', fontSize: 14 },
          }}
        />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />

          <Route path="/dashboard" element={<Private><Dashboard /></Private>} />
          <Route path="/upload" element={<Private><Upload /></Private>} />
          <Route path="/upcoming" element={<Private><Upcoming /></Private>} />
          <Route path="/history" element={<Private><History /></Private>} />
          <Route path="/today" element={<Private><TodayTasks /></Private>} />
          <Route path="/payment" element={<Private><Payment /></Private>} />
          <Route path="/profile" element={<Private><Profile /></Private>} />
          <Route path="/premium" element={<Private><PremiumLab /></Private>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
