import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login     from './pages/Login';
import Signup    from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Chat      from './pages/Chat';
import Tasks     from './pages/Tasks';
import Documents from './pages/Documents';
import Absences  from './pages/Absences';
import Admin     from './pages/Admin';
import Impressum  from './pages/legal/Impressum';
import Datenschutz from './pages/legal/Datenschutz';
import AGB        from './pages/legal/AGB';

function PrivateRoute({ children }) {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"  element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/chat"      element={<PrivateRoute><Chat /></PrivateRoute>} />
        <Route path="/tasks"     element={<PrivateRoute><Tasks /></PrivateRoute>} />
        <Route path="/documents" element={<PrivateRoute><Documents /></PrivateRoute>} />
        <Route path="/abwesenheiten" element={<PrivateRoute><Absences /></PrivateRoute>} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/impressum" element={<Impressum />} />
        <Route path="/datenschutz" element={<Datenschutz />} />
        <Route path="/agb" element={<AGB />} />
        <Route path="*"          element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;