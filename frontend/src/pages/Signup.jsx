import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import client from '../api/client';

export default function Signup() {
  const [orgName,  setOrgName]  = useState('');
  const [username, setUsername] = useState('');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const navigate                 = useNavigate();

  const handleSignup = async () => {
    if (!orgName || !username || !email || !password) {
      setError('Bitte alle Felder ausfüllen.'); return;
    }
    if (password.length < 6) {
      setError('Passwort muss mindestens 6 Zeichen haben.'); return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await client.post('/api/auth/signup', {
        organization_name: orgName,
        username,
        email,
        password,
      });
      localStorage.setItem('token',    res.data.access_token);
      localStorage.setItem('username', res.data.username);
      localStorage.setItem('role',     res.data.user_role);
      localStorage.setItem('user_id',  res.data.user_id);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registrierung fehlgeschlagen.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gx-aurora" style={s.page}>
      <div className="gx-card" style={s.card}>
        {/* Logo */}
        <div style={s.logoRow}>
          <span style={s.logoIcon}>➜]</span>
          <span style={s.logoText}>OnboardGuide AI</span>
        </div>
        <p style={s.tagline}>Registriere deine Firma und leg direkt los</p>

        <label style={s.label}>Firmenname</label>
        <div style={s.inputWrap}>
          <span style={s.inputIcon}>🏢</span>
          <input
            className="gx-input"
            style={s.input}
            placeholder="z.B. Acme GmbH"
            value={orgName}
            onChange={e => setOrgName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSignup()}
          />
        </div>

        <label style={s.label}>Dein Benutzername</label>
        <div style={s.inputWrap}>
          <span style={s.inputIcon}>👤</span>
          <input
            className="gx-input"
            style={s.input}
            placeholder="z.B. max_mueller"
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSignup()}
          />
        </div>

        <label style={s.label}>E-Mail</label>
        <div style={s.inputWrap}>
          <span style={s.inputIcon}>✉️</span>
          <input
            className="gx-input"
            style={s.input}
            type="email"
            placeholder="max@firma.de"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSignup()}
          />
        </div>

        <label style={s.label}>Passwort</label>
        <div style={s.inputWrap}>
          <span style={s.inputIcon}>🔒</span>
          <input
            className="gx-input"
            style={s.input}
            type="password"
            placeholder="Mindestens 6 Zeichen"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSignup()}
          />
        </div>

        <p style={s.note}>
          Du wirst automatisch erster Verwaltung-Account deiner neuen Firma.
        </p>

        {error && <p style={s.error}>{error}</p>}

        <button
          className="gx-btn"
          style={{...s.button, opacity: loading ? 0.7 : 1}}
          onClick={handleSignup}
          disabled={loading}
        >
          {loading ? 'Wird erstellt...' : 'Firma registrieren'}
        </button>

        <p style={s.hint}>
          Schon registriert? <span style={s.loginLink} onClick={() => navigate('/login')}>Zum Login</span>
        </p>

        <p style={s.legalHint}>
          Mit der Registrierung akzeptierst du die{' '}
          <Link to="/agb" style={s.legalLink}>AGB</Link> und die{' '}
          <Link to="/datenschutz" style={s.legalLink}>Datenschutzerklärung</Link>.
        </p>
      </div>
    </div>
  );
}

const s = {
  page:      { minHeight:'100vh', background:'#0d141c', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'Segoe UI, sans-serif', padding:'24px 0' },
  card:      { background:'transparent', borderRadius:'20px', padding:'48px', width:'420px', boxSizing:'border-box' },
  logoRow:   { display:'flex', alignItems:'center', gap:'12px', marginBottom:'6px' },
  logoIcon:  { fontSize:'32px' },
  logoText:  { color:'#eef3f7', fontSize:'26px', fontWeight:'700' },
  tagline:   { color:'#e3a24d', fontSize:'14px', marginBottom:'32px', marginTop:0 },
  label:     { color:'#8fa1ae', fontSize:'13px', fontWeight:'600', display:'block', marginBottom:'6px' },
  inputWrap: { position:'relative', display:'flex', alignItems:'center', marginBottom:'20px' },
  inputIcon: { position:'absolute', left:'14px', fontSize:'16px', zIndex:1 },
  input:     { width:'100%', padding:'13px 42px', background:'#0d141c', border:'1px solid #edb268', borderRadius:'10px', color:'#eef3f7', fontSize:'14px', outline:'none', boxSizing:'border-box' },
  note:      { color:'#748998', fontSize:'12px', marginTop:'-8px', marginBottom:'20px' },
  error:     { color:'#e0665a', fontSize:'13px', marginBottom:'12px', textAlign:'center' },
  button:    { width:'100%', padding:'14px', background:'#e3a24d', color:'#fff', border:'none', borderRadius:'10px', fontSize:'16px', fontWeight:'600', cursor:'pointer', marginBottom:'20px' },
  hint:      { color:'#748998', fontSize:'12px', textAlign:'center', margin:0 },
  loginLink: { color:'#e3a24d', cursor:'pointer', fontWeight:'600' },
  legalHint: { color:'#748998', fontSize:'11px', textAlign:'center', marginTop:'16px', lineHeight:'1.6' },
  legalLink: { color:'#8fa1ae', textDecoration:'underline' },
};
