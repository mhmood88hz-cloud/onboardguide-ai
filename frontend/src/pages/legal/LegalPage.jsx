import { Link } from 'react-router-dom';

export default function LegalPage({ title, updatedAt, children }) {
  return (
    <div className="gx-aurora" style={s.page}>
      <div className="gx-card" style={s.card}>
        <Link to="/login" style={s.back}>← Zurück</Link>
        <h1 style={s.title}>{title}</h1>
        <p style={s.updated}>Stand: {updatedAt}</p>
        <div style={s.body}>{children}</div>
      </div>
    </div>
  );
}

const s = {
  page:    { minHeight: '100vh', display: 'flex', justifyContent: 'center', padding: '48px 16px', fontFamily: '-apple-system, Segoe UI, sans-serif' },
  card:    { maxWidth: '680px', width: '100%', padding: '40px 44px', boxSizing: 'border-box' },
  back:    { color: '#8fa1ae', fontSize: '13px', textDecoration: 'none' },
  title:   { color: '#eef3f7', fontSize: '26px', fontWeight: '700', margin: '18px 0 4px' },
  updated: { color: '#748998', fontSize: '12px', margin: '0 0 28px' },
  body:    { color: '#b7c3cc', fontSize: '14px', lineHeight: '1.7', display: 'flex', flexDirection: 'column', gap: '20px' },
};

export const legalStyles = {
  h2: { color: '#eef3f7', fontSize: '15px', fontWeight: '600', margin: '0 0 8px' },
  a:  { color: '#e3a24d' },
};
