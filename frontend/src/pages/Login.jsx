import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const navigate                 = useNavigate();

  const handleLogin = async () => {
    if (!username || !password) { setError('Bitte alle Felder ausfüllen.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await client.post('/api/auth/login', { username, password });
      localStorage.setItem('token',    res.data.access_token);
      localStorage.setItem('username', res.data.username);
      localStorage.setItem('role',     res.data.user_role);
      localStorage.setItem('user_id',  res.data.user_id);
      navigate('/dashboard');
    } catch {
      setError('Benutzername oder Passwort falsch.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={s.page}>
      <div style={s.card}>
        {/* Logo */}
        <div style={s.logoRow}>
          <span style={s.logoIcon}>🤖</span>
          <span style={s.logoText}>OnboardGuide AI</span>
        </div>
        <p style={s.tagline}>Your intelligent onboarding companion</p>

        {/* Username */}
        <label style={s.label}>Email or Username</label>
        <div style={s.inputWrap}>
          <span style={s.inputIcon}>👤</span>
          <input
            style={s.input}
            placeholder="e.g. lisa_schmidt"
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLogin()}
          />
        </div>

        {/* Password */}
        <label style={s.label}>Password</label>
        <div style={s.inputWrap}>
          <span style={s.inputIcon}>🔒</span>
          <input
            style={s.input}
            type={showPw ? 'text' : 'password'}
            placeholder="••••••••••••"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLogin()}
          />
          <span
            style={s.eyeIcon}
            onClick={() => setShowPw(!showPw)}
          >
            {showPw ? '🙈' : '👁️'}
          </span>
        </div>

        {/* Remember + Forgot */}
        <div style={s.row}>
          <label style={s.checkRow}>
            <input type="checkbox" style={{marginRight:'6px'}} />
            <span style={{color:'#64748B', fontSize:'13px'}}>Remember me</span>
          </label>
          <span style={s.forgotLink}>Passwort vergessen? Kontaktiere HR.</span>
        </div>

        {/* Error */}
        {error && <p style={s.error}>{error}</p>}

        {/* Button */}
        <button
          style={{...s.button, opacity: loading ? 0.7 : 1}}
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? 'Wird eingeloggt...' : 'Log In'}
        </button>

        {/* Hint */}
        <p style={s.hint}>Zugang anfragen? Wende dich an die HR-Abteilung.</p>
      </div>
    </div>
  );
}

const s = {
  page:      { minHeight:'100vh', background:'#0A0E18', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'Segoe UI, sans-serif' },
  card:      { background:'#0F1929', border:'1px solid #1E293B', borderRadius:'20px', padding:'48px', width:'420px', boxSizing:'border-box' },
  logoRow:   { display:'flex', alignItems:'center', gap:'12px', marginBottom:'6px' },
  logoIcon:  { fontSize:'32px' },
  logoText:  { color:'#E2E8F0', fontSize:'26px', fontWeight:'700' },
  tagline:   { color:'#3B82F6', fontSize:'14px', marginBottom:'32px', marginTop:0 },
  label:     { color:'#94A3B8', fontSize:'13px', fontWeight:'600', display:'block', marginBottom:'6px' },
  inputWrap: { position:'relative', display:'flex', alignItems:'center', marginBottom:'20px' },
  inputIcon: { position:'absolute', left:'14px', fontSize:'16px', zIndex:1 },
  input:     { width:'100%', padding:'13px 42px', background:'#0A0E18', border:'1px solid #1E40AF', borderRadius:'10px', color:'#E2E8F0', fontSize:'14px', outline:'none', boxSizing:'border-box' },
  eyeIcon:   { position:'absolute', right:'14px', cursor:'pointer', fontSize:'16px' },
  row:       { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px' },
  checkRow:  { display:'flex', alignItems:'center', cursor:'pointer' },
  forgotLink:{ color:'#3B82F6', fontSize:'13px', cursor:'pointer' },
  error:     { color:'#EF4444', fontSize:'13px', marginBottom:'12px', textAlign:'center' },
  button:    { width:'100%', padding:'14px', background:'#3B82F6', color:'#fff', border:'none', borderRadius:'10px', fontSize:'16px', fontWeight:'600', cursor:'pointer', marginBottom:'20px' },
  hint:      { color:'#475569', fontSize:'12px', textAlign:'center', margin:0 },
};
