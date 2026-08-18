import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function Documents() {
  const navigate           = useNavigate();
  const username           = localStorage.getItem('username');
  const role               = localStorage.getItem('role');
  const userId             = localStorage.getItem('user_id');
  const [docs, setDocs]    = useState([]);
  const [loading, setLoading]   = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle]       = useState('');
  const [category, setCategory] = useState('Allgemein');
  const [newCategory, setNewCategory] = useState('');
  const [users, setUsers]       = useState([]);
  const [uploadedBy, setUploadedBy] = useState(userId);
  const [file, setFile]         = useState(null);
  const fileRef                 = useRef();

  const BASE_CATEGORIES = ['Allgemein','IT','HR','Finanzen','Recht','Marketing','Alpha-Projekt'];

  const loadDocs = () => {
    client.get('/api/documents')
      .then(res => setDocs(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadDocs(); }, []);

  useEffect(() => {
    if (role === 'Verwaltung') {
      client.get('/api/users')
        .then(res => setUsers(res.data))
        .catch(err => console.error(err));
    }
  }, [role]);

  const handleUpload = async () => {
    const finalCategory = category === '__new__' ? newCategory.trim() : category;
    if (!title || !file) { alert('Bitte Titel und Datei angeben.'); return; }
    if (!finalCategory) { alert('Bitte eine Kategorie angeben.'); return; }

    setUploading(true);
    const form = new FormData();
    form.append('title', title);
    form.append('category', finalCategory);
    form.append('uploaded_by', uploadedBy);
    form.append('file', file);

    try {
      await client.post('/api/documents/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setShowForm(false);
      setTitle('');
      setFile(null);
      setCategory('Allgemein');
      setNewCategory('');
      setUploadedBy(userId);
      loadDocs();
    } catch {
      alert('Fehler beim Hochladen.');
    } finally {
      setUploading(false);
    }
  };

  const categoryColor = (cat) => {
    const map = {
      'IT':           { bg:'#1E293B', color:'#7DD3FC' },
      'Allgemein':    { bg:'#1E293B', color:'#94A3B8' },
      'HR':           { bg:'#1E293B', color:'#A78BFA' },
      'Finanzen':     { bg:'#2D1B00', color:'#F59E0B' },
      'Recht':        { bg:'#2D1B6E', color:'#A78BFA' },
      'Marketing':    { bg:'#022C22', color:'#34D399' },
    };
    return map[cat] || { bg:'#1E293B', color:'#94A3B8' };
  };

  return (
    <div style={s.page}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>🤖 OnboardGuide AI</div>
        <nav>
          <div style={s.navItem} onClick={() => navigate('/dashboard')}>📊 Dashboard</div>
          <div style={s.navItem} onClick={() => navigate('/chat')}>💬 Chat-Assistent</div>
          <div style={s.navItem} onClick={() => navigate('/tasks')}>☰ Meine Aufgaben</div>
          {role === 'Verwaltung' && (
            <div style={{...s.navItem, ...s.navActive}}>📄 Dokumente</div>
          )}
        </nav>
        <div style={s.userInfo}>
          <span style={{fontSize:'28px'}}>👤</span>
          <div>
            <div style={s.userName}>{username}</div>
            <div style={s.userRole}>{role}</div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={s.main}>
        <div style={s.header}>
          <div>
            <h1 style={s.title}>Dokumente</h1>
            <p style={s.subtitle}>Hochgeladene Firmendokumente</p>
          </div>
          {role === 'Verwaltung' && (
            <button style={s.uploadBtn} onClick={() => setShowForm(!showForm)}>
              + Hochladen
            </button>
          )}
        </div>

        {/* Upload Form */}
        {showForm && (
          <div style={s.form}>
            <input
              style={s.input}
              placeholder="Dokumenttitel"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
            <select
              style={s.input}
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              {BASE_CATEGORIES.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
              <option value="__new__">+ Neue Kategorie...</option>
            </select>
            {category === '__new__' && (
              <input
                style={s.input}
                placeholder="Name der neuen Kategorie"
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
              />
            )}
            <select
              style={s.input}
              value={uploadedBy}
              onChange={e => setUploadedBy(e.target.value)}
            >
              <option value={userId}>Automatisch: {username} (ich)</option>
              {users.filter(u => String(u.id) !== String(userId)).map(u => (
                <option key={u.id} value={u.id}>
                  {u.username} ({u.user_role}{u.assigned_project ? ` – ${u.assigned_project}` : ''})
                </option>
              ))}
            </select>
            <input
              type="file"
              ref={fileRef}
              accept=".pdf,.txt"
              style={{display:'none'}}
              onChange={e => setFile(e.target.files[0])}
            />
            <button style={s.fileBtn} onClick={() => fileRef.current.click()}>
              {file ? `📄 ${file.name}` : '📁 Datei auswählen'}
            </button>
            <div style={{display:'flex', gap:'12px'}}>
              <button style={s.submitBtn} onClick={handleUpload} disabled={uploading}>
                {uploading ? 'Wird hochgeladen...' : 'Hochladen'}
              </button>
              <button style={s.cancelBtn} onClick={() => setShowForm(false)}>
                Abbrechen
              </button>
            </div>
          </div>
        )}

        {/* Documents Table */}
        <div style={s.table}>
          <div style={s.tableHeader}>
            <span style={{flex:3}}>DOKUMENT</span>
            <span style={{flex:1}}>KATEGORIE</span>
            <span style={{flex:1}}>CHUNKS</span>
            <span style={{flex:1}}>STATUS</span>
            <span style={{width:'40px'}}></span>
          </div>

          {loading ? (
            <div style={{padding:'24px', color:'#64748B'}}>Laden...</div>
          ) : docs.length === 0 ? (
            <div style={{padding:'24px', color:'#64748B'}}>Keine Dokumente vorhanden.</div>
          ) : docs.map(doc => {
            const cat = categoryColor(doc.category);
            return (
              <div key={doc.id} style={s.tableRow}>
                <div style={{flex:3, display:'flex', alignItems:'center', gap:'12px'}}>
                  <span style={{color:'#1E40AF', fontSize:'20px'}}>📄</span>
                  <span style={{color:'#E2E8F0', fontWeight:'500'}}>{doc.title}</span>
                </div>
                <div style={{flex:1}}>
                  <span style={{
                    background: cat.bg,
                    color: cat.color,
                    padding:'4px 10px',
                    borderRadius:'6px',
                    fontSize:'12px',
                    fontWeight:'600'
                  }}>
                    {doc.category}
                  </span>
                </div>
                <div style={{flex:1, color:'#64748B', fontSize:'14px'}}>
                  {doc.chunk_count != null ? `${doc.chunk_count} Chunks` : '–'}
                </div>
                <div style={{flex:1, display:'flex', alignItems:'center', gap:'6px'}}>
                  <span style={{
                    width:'8px', height:'8px', borderRadius:'50%',
                    background: doc.content ? '#34D399' : '#F59E0B',
                    display:'inline-block'
                  }} />
                  <span style={{color:'#64748B', fontSize:'13px'}}>
                    {doc.content ? 'Verarbeitet' : 'Kein Text'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const s = {
  page:        { display:'flex', minHeight:'100vh', background:'#0A0E18' },
  sidebar:     { width:'240px', background:'#10192B', borderRight:'1px solid #1E293B', display:'flex', flexDirection:'column', padding:'24px 0' },
  logo:        { color:'#E2E8F0', fontWeight:'700', fontSize:'16px', padding:'0 20px 32px' },
  navItem:     { color:'#64748B', padding:'12px 20px', cursor:'pointer', fontSize:'14px' },
  navActive:   { color:'#E2E8F0', background:'#1E293B', borderRight:'3px solid #1E40AF' },
  userInfo:    { display:'flex', alignItems:'center', gap:'12px', padding:'20px', borderTop:'1px solid #1E293B', marginTop:'auto' },
  userName:    { color:'#E2E8F0', fontSize:'13px', fontWeight:'600' },
  userRole:    { color:'#64748B', fontSize:'11px' },
  main:        { flex:1, padding:'40px' },
  header:      { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'24px' },
  title:       { color:'#E2E8F0', fontSize:'28px', fontWeight:'700', margin:'0 0 4px' },
  subtitle:    { color:'#64748B', margin:0 },
  uploadBtn:   { background:'#1E40AF', color:'#fff', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'14px' },
  form:        { background:'#10192B', border:'1px solid #1E293B', borderRadius:'12px', padding:'24px', marginBottom:'24px', display:'flex', flexDirection:'column', gap:'12px' },
  input:       { padding:'12px 16px', background:'#0A0E18', border:'1px solid #1E293B', borderRadius:'8px', color:'#E2E8F0', fontSize:'14px', outline:'none' },
  fileBtn:     { padding:'12px 16px', background:'#0A0E18', border:'1px dashed #334155', borderRadius:'8px', color:'#64748B', cursor:'pointer', textAlign:'left', fontSize:'14px' },
  submitBtn:   { background:'#1E40AF', color:'#fff', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  cancelBtn:   { background:'#1E293B', color:'#64748B', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer' },
  table:       { background:'#10192B', border:'1px solid #1E293B', borderRadius:'12px', overflow:'hidden' },
  tableHeader: { display:'flex', padding:'16px 20px', borderBottom:'1px solid #1E293B', color:'#475569', fontSize:'11px', fontWeight:'700', letterSpacing:'1px' },
  tableRow:    { display:'flex', alignItems:'center', padding:'16px 20px', borderBottom:'1px solid #0F172A', gap:'12px' },
};
