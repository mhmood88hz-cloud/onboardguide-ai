import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function Documents() {
  const navigate           = useNavigate();
  const username           = localStorage.getItem('username');
  const role               = localStorage.getItem('role');
  const [docs, setDocs]    = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/api/documents')
      .then(res => setDocs(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = (id) => {
    client.delete(`/api/documents/${id}`)
      .then(() => setDocs(docs.filter(d => d.id !== id)))
      .catch(err => console.error(err));
  };

  return (
    <div style={styles.page}>
      {/* Sidebar */}
      <div style={styles.sidebar}>
        <div style={styles.logo}>🤖 OnboardGuide AI</div>
        <nav style={styles.nav}>
          <div style={styles.navItem} onClick={() => navigate('/dashboard')}>📊 Dashboard</div>
          <div style={styles.navItem} onClick={() => navigate('/chat')}>💬 Chat-Assistent</div>
          <div style={styles.navItem} onClick={() => navigate('/tasks')}>✅ Meine Aufgaben</div>
          {role === 'Verwaltung' && (
            <div style={{...styles.navItem, ...styles.navActive}}>📄 Dokumente</div>
          )}
        </nav>
        <div style={styles.userInfo}>
          <div style={styles.userAvatar}>👤</div>
          <div>
            <div style={styles.userName}>{username}</div>
            <div style={styles.userRole}>{role}</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={styles.main}>
        <div style={styles.header}>
          <div>
            <h1 style={styles.title}>Dokumente</h1>
            <p style={styles.subtitle}>Hochgeladene Firmendokumente</p>
          </div>
          <button style={styles.uploadBtn} onClick={() => alert('Upload-Dialog öffnen')}>+ Hochladen</button>
        </div>

        {/* Documents Table Card */}
        <div style={styles.card}>
          <div style={styles.tableHeader}>
            <span style={styles.th}>DOKUMENT</span>
            <span style={styles.th}>KATEGORIE</span>
            <span style={styles.th}>CHUNKS</span>
            <span style={styles.th}>WÖRTER</span>
            <span style={styles.th}>STATUS</span>
            <span style={styles.th}></span>
          </div>

          {loading ? (
            <p style={{color:'#64748B', padding:'20px'}}>Laden...</p>
          ) : docs.length === 0 ? (
            <p style={{color:'#64748B', padding:'20px'}}>Keine Dokumente vorhanden.</p>
          ) : (
            docs.map(doc => (
              <div key={doc.id} style={styles.tableRow}>
                <span style={styles.docName}>📄 {doc.title}</span>
                <span><span style={styles.categoryBadge}>{doc.category}</span></span>
                <span style={styles.tdDim}>{doc.chunks} Chunks</span>
                <span style={styles.tdDim}>{doc.words} Wörter</span>
                <span>
                  <span style={doc.status === 'Verarbeitet' ? styles.statusGreen : styles.statusYellow}>
                    ● {doc.status}
                  </span>
                </span>
                <span style={{textAlign: 'right'}}>
                  <button style={styles.deleteBtn} onClick={() => handleDelete(doc.id)}>🗑</button>
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  page:          { display:'flex', minHeight:'100vh', background:'#0A0E18' },
  sidebar:       { width:'240px', background:'#10192B', borderRight:'1px solid #1E293B', display:'flex', flexDirection:'column', padding:'24px 0' },
  logo:          { color:'#E2E8F0', fontWeight:'700', fontSize:'16px', padding:'0 20px 32px' },
  nav:           { flex:1 },
  navItem:       { color:'#64748B', padding:'12px 20px', cursor:'pointer', fontSize:'14px', display:'flex', alignItems:'center', gap:'8px' },
  navActive:     { color:'#E2E8F0', background:'#1E293B', borderRight:'3px solid #1E40AF' },
  userInfo:      { display:'flex', alignItems:'center', gap:'12px', padding:'20px', borderTop:'1px solid #1E293B' },
  userAvatar:    { fontSize:'28px' },
  userName:      { color:'#E2E8F0', fontSize:'13px', fontWeight:'600' },
  userRole:      { color:'#64748B', fontSize:'11px' },
  main:          { flex:1, padding:'40px' },
  header:        { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'32px' },
  title:         { color:'#E2E8F0', fontSize:'28px', fontWeight:'700', margin:'0 0 4px' },
  subtitle:      { color:'#64748B', margin:0 },
  uploadBtn:     { background:'#3b82f6', color:'#fff', border:'none', padding:'10px 20px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  card:          { background:'#10192B', border:'1px solid #1E293B', borderRadius:'12px', padding:'16px 24px' },
  tableHeader:   { display:'grid', gridTemplateColumns:'2fr 1fr 1fr 1fr 1fr 40px', padding:'12px 0', borderBottom:'1px solid #1E293B', color:'#64748B', fontSize:'11px', fontWeight:'700', letterSpacing:'1px' },
  tableRow:      { display:'grid', gridTemplateColumns:'2fr 1fr 1fr 1fr 1fr 40px', alignItems:'center', padding:'16px 0', borderBottom:'1px solid #1E293B', fontSize:'14px' },
  docName:       { color:'#E2E8F0', fontWeight:'500' },
  categoryBadge: { background:'#1e3a8a', color:'#93c5fd', padding:'4px 10px', borderRadius:'6px', fontSize:'11px', fontWeight:'500' },
  tdDim:         { color:'#64748B' },
  statusGreen:   { color:'#34D399', fontSize:'12px' },
  statusYellow:  { color:'#fbbf24', fontSize:'12px' },
  deleteBtn:     { background:'transparent', border:'none', color:'#ef4444', cursor:'pointer', fontSize:'16px' }
};
};