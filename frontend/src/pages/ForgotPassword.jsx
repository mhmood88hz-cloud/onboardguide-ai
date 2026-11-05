import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function ForgotPassword() {
  const [email,   setEmail]   = useState('');
  const [message, setMessage] = useState('');
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);
  const navigate               = useNavigate();

  const handleSubmit = async () => {
    if (!email) { setError('Bitte E-Mail-Adresse eingeben.'); return; }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const res = await client.post('/api/auth/forgot-password', { email });
      setMessage(res.data.message);
    } catch {
      setError('Etwas ist schiefgelaufen. Bitte später erneut versuchen.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gx-aurora" style={s.page}>
      <div className="gx-card" style={s.card}>
        <div style={s.logoRow}>
          <span style={s.logoIcon}>➜]</span>
          <span style={s.logoText}>OnboardGuide AI</span>
        </div>
        <p style={s.tagline}>Passwort zurücksetzen</p>

        {!message && (
          <>
            <label style={s.label}>E-Mail-Adresse</label>
            <div style={s.inputWrap}>
              <span style={s.inputIcon}>✉️</span>
              <input
                className="gx-input"
                style={s.input}
                type="email"
                placeholder="max@firma.de"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              />
            </div>

            {error && <p style={s.error}>{error}</p>}

            <button
              className="gx-btn"
              style={{...s.button, opacity: loading ? 0.7 : 1}}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Wird gesendet...' : 'Link anfordern'}
            </button>
          </>
        )}

        {message && <p style={s.success}>{message}</p>}

        <p style={s.hint}>
          <span style={s.loginLink} onClick={() => navigate('/login')}>Zurück zum Login</span>
        </p>
      </div>
    </div>
  );
}

const s = {
  page:      { minHeight:'100vh', background:'#0d141c', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'Segoe UI, sans-serif' },
  card:      { background:'transparent', borderRadius:'20px', padding:'48px', width:'420px', boxSizing:'border-box' },
  logoRow:   { display:'flex', alignItems:'center', gap:'12px', marginBottom:'6px' },
  logoIcon:  { fontSize:'32px' },
  logoText:  { color:'#eef3f7', fontSize:'26px', fontWeight:'700' },
  tagline:   { color:'#e3a24d', fontSize:'14px', marginBottom:'32px', marginTop:0 },
  label:     { color:'#8fa1ae', fontSize:'13px', fontWeight:'600', display:'block', marginBottom:'6px' },
  inputWrap: { position:'relative', display:'flex', alignItems:'center', marginBottom:'20px' },
  inputIcon: { position:'absolute', left:'14px', fontSize:'16px', zIndex:1 },
  input:     { width:'100%', padding:'13px 42px', background:'#0d141c', border:'1px solid #edb268', borderRadius:'10px', color:'#eef3f7', fontSize:'14px', outline:'none', boxSizing:'border-box' },
  error:     { color:'#e0665a', fontSize:'13px', marginBottom:'12px', textAlign:'center' },
  success:   { color:'#6fcf97', fontSize:'14px', textAlign:'center', marginBottom:'20px', lineHeight:'1.6' },
  button:    { width:'100%', padding:'14px', background:'#e3a24d', color:'#fff', border:'none', borderRadius:'10px', fontSize:'16px', fontWeight:'600', cursor:'pointer', marginBottom:'20px' },
  hint:      { color:'#748998', fontSize:'12px', textAlign:'center', margin:'8px 0 0' },
  loginLink: { color:'#e3a24d', cursor:'pointer', fontWeight:'600' },
};
