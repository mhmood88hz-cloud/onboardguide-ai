import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

// ── Passwort ändern Modal ─────────────────────────────────────────────────
function ChangePwModal({ onClose }) {
  const [oldPw,   setOldPw]   = useState('');
  const [newPw,   setNewPw]   = useState('');
  const [loading, setLoading] = useState(false);
  const [msg,     setMsg]     = useState('');

  const handle = async () => {
    if (!oldPw || !newPw) { setMsg('Bitte alle Felder ausfüllen.'); return; }
    setLoading(true);
    try {
      await client.post('/api/auth/change-password', {
        old_password: oldPw, new_password: newPw
      });
      setMsg('✅ Passwort erfolgreich geändert.');
      setTimeout(onClose, 1500);
    } catch {
      setMsg('❌ Altes Passwort falsch.');
    } finally { setLoading(false); }
  };

  return (
    <div className="gx-modal-overlay" style={m.overlay}>
      <div className="gx-modal" style={m.modal}>
        <div style={m.header}>
          <h2 style={{color:'#eef3f7', margin:0}}>Passwort ändern</h2>
          <button className="gx-btn" style={m.close} onClick={onClose}>✕</button>
        </div>
        <label style={m.label}>Aktuelles Passwort</label>
        <input className="gx-input" style={m.input} type="password" value={oldPw} onChange={e => setOldPw(e.target.value)} />
        <label style={m.label}>Neues Passwort</label>
        <input className="gx-input" style={m.input} type="password" value={newPw} onChange={e => setNewPw(e.target.value)} />
        {msg && <p style={{color: msg.startsWith('✅') ? '#4caf6d' : '#e0665a', fontSize:'13px'}}>{msg}</p>}
        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button className="gx-btn" style={m.btn} onClick={handle} disabled={loading}>{loading ? 'Wird gespeichert...' : 'Ändern'}</button>
          <button className="gx-btn" style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Passwort zurücksetzen Modal ───────────────────────────────────────────
function ResetPwModal({ member, onClose }) {
  const [newPw,   setNewPw]   = useState('');
  const [loading, setLoading] = useState(false);
  const [msg,     setMsg]     = useState('');

  const handle = async () => {
    if (!newPw) { setMsg('Bitte Passwort eingeben.'); return; }
    setLoading(true);
    try {
      await client.post('/api/auth/reset-password', {
        user_id: member.id, new_password: newPw
      });
      setMsg(`✅ Passwort von '${member.username}' zurückgesetzt.`);
      setTimeout(onClose, 1500);
    } catch {
      setMsg('❌ Fehler beim Zurücksetzen.');
    } finally { setLoading(false); }
  };

  return (
    <div className="gx-modal-overlay" style={m.overlay}>
      <div className="gx-modal" style={m.modal}>
        <div style={m.header}>
          <h2 style={{color:'#eef3f7', margin:0}}>Passwort zurücksetzen</h2>
          <button className="gx-btn" style={m.close} onClick={onClose}>✕</button>
        </div>
        <p style={{color:'#8fa1ae', marginBottom:'16px', fontSize:'14px'}}>
          Neues Passwort für <b style={{color:'#eef3f7'}}>{member.username}</b>
        </p>
        <label style={m.label}>Neues Passwort</label>
        <input className="gx-input" style={m.input} type="password" value={newPw} onChange={e => setNewPw(e.target.value)} />
        {msg && <p style={{color: msg.startsWith('✅') ? '#4caf6d' : '#e0665a', fontSize:'13px'}}>{msg}</p>}
        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button className="gx-btn" style={m.btn} onClick={handle} disabled={loading}>{loading ? 'Wird gesetzt...' : 'Zurücksetzen'}</button>
          <button className="gx-btn" style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Neuer Benutzer Modal (nur Verwaltung) ─────────────────────────────────
function NewUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    username: '', email: '', password: '',
    user_role: 'Mitarbeiter', department: '',
    assigned_project: '', reports_to: ''
  });
  const [loading, setLoading] = useState(false);
  const [msg,     setMsg]     = useState('');

  const set = (k, v) => setForm(f => ({...f, [k]: v}));

  const handle = async () => {
    if (!form.username || !form.email || !form.password) {
      setMsg('Benutzername, E-Mail und Passwort sind Pflichtfelder.'); return;
    }
    setLoading(true);
    try {
      await client.post('/api/auth/register', {
        username:         form.username,
        email:            form.email,
        password:         form.password,
        user_role:        form.user_role,
        department:       form.department   || null,
        assigned_project: form.assigned_project || null,
        reports_to:       form.reports_to   ? parseInt(form.reports_to) : null,
      });
      setMsg(`✅ Benutzer '${form.username}' erstellt.`);
      setTimeout(() => { onCreated(); onClose(); }, 1200);
    } catch (err) {
      setMsg('❌ ' + (err.response?.data?.detail || 'Fehler beim Erstellen.'));
    } finally { setLoading(false); }
  };

  return (
    <div className="gx-modal-overlay" style={m.overlay}>
      <div className="gx-modal" style={{...m.modal, maxWidth:'480px', maxHeight:'90vh', overflowY:'auto'}}>
        <div style={m.header}>
          <h2 style={{color:'#eef3f7', margin:0}}>Neuer Benutzer</h2>
          <button className="gx-btn" style={m.close} onClick={onClose}>✕</button>
        </div>

        <label style={m.label}>Benutzername *</label>
        <input className="gx-input" style={m.input} placeholder="z.B. max_mueller"
               value={form.username} onChange={e => set('username', e.target.value)} />

        <label style={m.label}>E-Mail *</label>
        <input className="gx-input" style={m.input} placeholder="max@firma.de" type="email"
               value={form.email} onChange={e => set('email', e.target.value)} />

        <label style={m.label}>Passwort *</label>
        <input className="gx-input" style={m.input} type="password" placeholder="Mindestens 6 Zeichen"
               value={form.password} onChange={e => set('password', e.target.value)} />

        <label style={m.label}>Rolle</label>
        <select className="gx-input" style={m.input} value={form.user_role} onChange={e => set('user_role', e.target.value)}>
          <option value="Mitarbeiter">Mitarbeiter</option>
          <option value="Leader">Leader</option>
          <option value="Verwaltung">Verwaltung</option>
        </select>

        <label style={m.label}>Abteilung</label>
        <input className="gx-input" style={m.input} placeholder="z.B. IT, Marketing, HR"
               value={form.department} onChange={e => set('department', e.target.value)} />

        <label style={m.label}>Projekt</label>
        <input className="gx-input" style={m.input} placeholder="z.B. Alpha-Projekt"
               value={form.assigned_project} onChange={e => set('assigned_project', e.target.value)} />

        <label style={m.label}>Leader ID (reports_to)</label>
        <input className="gx-input" style={m.input} placeholder="ID des direkten Leaders"
               value={form.reports_to} onChange={e => set('reports_to', e.target.value)} />

        {msg && <p style={{color: msg.startsWith('✅') ? '#4caf6d' : '#e0665a', fontSize:'13px'}}>{msg}</p>}

        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button className="gx-btn" style={m.btn} onClick={handle} disabled={loading}>
            {loading ? 'Wird erstellt...' : 'Benutzer anlegen'}
          </button>
          <button className="gx-btn" style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Neue Aufgabe Modal ────────────────────────────────────────────────────
function NewTaskModal({ team, onClose, onCreated }) {
  const userId = localStorage.getItem('user_id');
  const [form, setForm] = useState({
    title: '', description: '', task_type: 'Onboarding',
    project_name: '', assigned_to: ''
  });
  const [loading, setLoading] = useState(false);

  const set = (k, v) => setForm(f => ({...f, [k]: v}));

  const handle = async () => {
    if (!form.title || !form.assigned_to) {
      alert('Titel und Mitarbeiter sind Pflichtfelder.'); return;
    }
    setLoading(true);
    try {
      await client.post('/api/tasks', {
        title:        form.title,
        description:  form.description  || null,
        task_type:    form.task_type,
        project_name: form.project_name || null,
        assigned_to:  parseInt(form.assigned_to),
        assigned_by:  parseInt(userId),
      });
      onCreated();
      onClose();
    } catch {
      alert('Fehler beim Erstellen der Aufgabe.');
    } finally { setLoading(false); }
  };

  return (
    <div className="gx-modal-overlay" style={m.overlay}>
      <div className="gx-modal" style={{...m.modal, maxWidth:'480px'}}>
        <div style={m.header}>
          <h2 style={{color:'#eef3f7', margin:0}}>Neue Aufgabe erstellen</h2>
          <button className="gx-btn" style={m.close} onClick={onClose}>✕</button>
        </div>

        <label style={m.label}>Titel *</label>
        <input className="gx-input" style={m.input} placeholder="z.B. VPN einrichten"
               value={form.title} onChange={e => set('title', e.target.value)} />

        <label style={m.label}>Beschreibung</label>
        <textarea className="gx-input" style={{...m.input, height:'80px', resize:'vertical'}}
                  placeholder="Was muss genau gemacht werden?"
                  value={form.description} onChange={e => set('description', e.target.value)} />

        <label style={m.label}>Typ</label>
        <select className="gx-input" style={m.input} value={form.task_type} onChange={e => set('task_type', e.target.value)}>
          <option value="Onboarding">Onboarding</option>
          <option value="Projekt">Projekt</option>
        </select>

        <label style={m.label}>Projektname</label>
        <input className="gx-input" style={m.input} placeholder="z.B. Alpha-Projekt (optional)"
               value={form.project_name} onChange={e => set('project_name', e.target.value)} />

        <label style={m.label}>Mitarbeiter *</label>
        <select className="gx-input" style={m.input} value={form.assigned_to} onChange={e => set('assigned_to', e.target.value)}>
          <option value="">Bitte auswählen</option>
          {team.map(u => (
            <option key={u.id} value={u.id}>
              {u.username} ({u.department || 'Allgemein'})
            </option>
          ))}
        </select>

        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button className="gx-btn" style={m.btn} onClick={handle} disabled={loading}>
            {loading ? 'Wird erstellt...' : 'Aufgabe erstellen'}
          </button>
          <button className="gx-btn" style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate  = useNavigate();
  const username  = localStorage.getItem('username');
  const role      = localStorage.getItem('role');
  const userId    = localStorage.getItem('user_id');

  const [tasks,   setTasks]   = useState([]);
  const [team,    setTeam]    = useState([]);
  const [loading, setLoading] = useState(true);

  const [showChangePw,  setShowChangePw]  = useState(false);
  const [resetMember,   setResetMember]   = useState(null);
  const [showNewUser,   setShowNewUser]   = useState(false);
  const [showNewTask,   setShowNewTask]   = useState(false);

  const loadTasks = () => {
    client.get(`/api/tasks?user_id=${userId}`)
      .then(res => setTasks(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  const loadTeam = () => {
    if (role === 'Leader') {
      client.get(`/api/tasks/leader/progress?leader_id=${userId}`)
        .then(res => setTeam(res.data)).catch(console.error);
    } else if (role === 'Verwaltung') {
      client.get('/api/users')
        .then(res => setTeam(res.data)).catch(console.error);
    }
  };

  useEffect(() => { loadTasks(); loadTeam(); }, [userId]);

  const completed = tasks.filter(t => t.is_completed).length;
  const total     = tasks.length;
  const progress  = total > 0 ? Math.round((completed / total) * 100) : 0;
  const next      = tasks.find(t => !t.is_completed);

  const handleDelete = async (memberId, memberName) => {
    if (!window.confirm(`Benutzer '${memberName}' wirklich löschen?`)) return;
    try {
      await client.delete(`/api/users/${memberId}`);
      loadTeam();
    } catch { alert('Fehler beim Löschen.'); }
  };

  const canManageTeam = role === 'Leader' || role === 'Verwaltung';

  return (
    <div className="gx-aurora" style={s.page}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>🤖 OnboardGuide AI</div>
        <nav>
          <div className="gx-nav-item" style={{...s.navItem, ...s.navActive}}>📊 Dashboard</div>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/chat')}>💬 Chat-Assistent</div>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/tasks')}>☰ Meine Aufgaben</div>
          {role === 'Verwaltung' && (
            <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/documents')}>📄 Dokumente</div>
          )}
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/abwesenheiten')}>🌴 Abwesenheiten</div>
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
        {/* Header */}
        <div style={s.header}>
          <div>
            <h1 style={s.welcome}>Willkommen zurück, {username}! 👋</h1>
            <p style={s.subtitle}>Lass uns da weitermachen, wo du aufgehört hast.</p>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:'10px', flexWrap:'wrap'}}>
            <div style={s.dayBadge}>📅 Onboarding läuft</div>
            {role === 'Verwaltung' && (
              <button className="gx-btn" style={s.newUserBtn} onClick={() => setShowNewUser(true)}>
                👤 Neuer Benutzer
              </button>
            )}
            <button className="gx-btn" style={s.pwBtn} onClick={() => setShowChangePw(true)}>🔑 Passwort</button>
            <button className="gx-btn" style={s.logoutBtn} onClick={() => { localStorage.clear(); navigate('/login'); }}>
              Ausloggen
            </button>
          </div>
        </div>

        {/* Progress Card */}
        <div className="gx-card gx-card--hover" style={s.card}>
          <div style={s.cardHeader}>
            <div>
              <h2 style={s.cardTitle}>Dein Onboarding-Status</h2>
              <p style={s.cardSubtitle}>{completed} von {total} Aufgaben abgeschlossen</p>
            </div>
            <div style={s.progressPercent}>{progress}% abgeschlossen</div>
          </div>
          <div style={s.progressBar}>
            <div style={{...s.progressFill, width:`${progress}%`}} />
          </div>
          {next && (
            <p style={s.nextMilestone}>
              Nächster Meilenstein:&nbsp;
              <span style={{color:'#edb268', fontWeight:'600'}}>{next.title}</span>
            </p>
          )}
        </div>

        {/* Team Block */}
        {canManageTeam && (
          <div className="gx-card gx-card--hover" style={s.card}>
            <div style={s.cardHeader}>
              <div>
                <h2 style={s.cardTitle}>
                  {role === 'Verwaltung' ? 'Alle Benutzer' : 'Mein Team'}
                </h2>
                <p style={s.cardSubtitle}>{team.length} Mitarbeiter</p>
              </div>
              <button className="gx-btn" style={s.newTaskBtn} onClick={() => setShowNewTask(true)}>
                + Neue Aufgabe
              </button>
            </div>

            {team.length === 0 ? (
              <p style={{color:'#8fa1ae'}}>Keine Mitarbeiter gefunden.</p>
            ) : team.map(member => {
              const p   = member.progress_percent || 0;
              const col = p >= 75 ? '#4caf6d' : p >= 40 ? '#edb268' : '#d9a83e';
              return (
                <div key={member.id} className="gx-row" style={s.memberRow}>
                  <span style={{fontSize:'24px'}}>👤</span>
                  <div style={{flex:1}}>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'6px'}}>
                      <div>
                        <span style={{color:'#eef3f7', fontWeight:'600', fontSize:'14px'}}>
                          {member.username}
                        </span>
                        <span style={{color:'#8fa1ae', fontSize:'12px', marginLeft:'8px'}}>
                          {member.department || 'Allgemein'} · {member.user_role}
                        </span>
                      </div>
                      <span style={{color:col, fontWeight:'700', fontSize:'14px'}}>{p}%</span>
                    </div>
                    <div style={s.progressBar}>
                      <div style={{...s.progressFill, width:`${p}%`, background:col}} />
                    </div>
                  </div>
                  <div style={{display:'flex', gap:'6px'}}>
                    <button className="gx-btn" style={s.viewBtn}
                      onClick={() => navigate(`/tasks?user_id=${member.id}&name=${member.username}`)}>
                      →
                    </button>
                    <button className="gx-btn" style={s.resetPwBtn} onClick={() => setResetMember(member)} title="Passwort zurücksetzen">
                      🔑
                    </button>
                    {role === 'Verwaltung' && (
                      <button className="gx-btn" style={s.deleteBtn}
                        onClick={() => handleDelete(member.id, member.username)} title="Löschen">
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Tasks Card */}
        <div className="gx-card gx-card--hover" style={s.card}>
          <div style={s.cardHeader}>
            <h2 style={s.cardTitle}>Deine Aufgaben</h2>
            <span style={s.badge}>{total - completed} verbleibend</span>
          </div>
          {loading ? (
            <p style={{color:'#8fa1ae', padding:'16px 0'}}>Laden...</p>
          ) : tasks.length === 0 ? (
            <p style={{color:'#8fa1ae', padding:'16px 0'}}>Keine Aufgaben vorhanden.</p>
          ) : tasks.slice(0, 5).map(task => (
            <div key={task.id} className="gx-row" style={{...s.taskRow, ...(task === next ? s.taskActive : {})}}>
              <span style={task.is_completed ? s.checkDone : s.checkOpen}>
                {task.is_completed ? '✓' : '○'}
              </span>
              <div style={{flex:1}}>
                <div style={{
                  color: task.is_completed ? '#8fa1ae' : '#eef3f7',
                  textDecoration: task.is_completed ? 'line-through' : 'none',
                  fontWeight:'500', fontSize:'15px',
                }}>
                  {task.title}
                </div>
                {task === next && task.description && (
                  <div style={{color:'#8fa1ae', fontSize:'12px', marginTop:'2px'}}>{task.description}</div>
                )}
              </div>
              {task.is_completed && <span style={s.doneBadge}>erledigt</span>}
              {!task.is_completed && task === next && (
                <>
                  <span style={s.activeBadge}>in Bearbeitung</span>
                  <button className="gx-btn" style={s.continueBtn} onClick={() => navigate('/tasks')}>Fortsetzen</button>
                </>
              )}
              {!task.is_completed && task !== next && (
                <>
                  <span style={s.openBadge}>offen</span>
                  <button className="gx-btn" style={s.startBtn} onClick={() => navigate('/tasks')}>Starten</button>
                </>
              )}
            </div>
          ))}
          {tasks.length > 5 && (
            <div style={{padding:'14px 0', color:'#edb268', cursor:'pointer', fontSize:'14px', textAlign:'center'}}
                 onClick={() => navigate('/tasks')}>
              Alle {tasks.length} Aufgaben anzeigen →
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showChangePw && <ChangePwModal onClose={() => setShowChangePw(false)} />}
      {resetMember  && <ResetPwModal member={resetMember} onClose={() => setResetMember(null)} />}
      {showNewUser  && <NewUserModal onClose={() => setShowNewUser(false)} onCreated={loadTeam} />}
      {showNewTask  && <NewTaskModal team={team} onClose={() => setShowNewTask(false)} onCreated={loadTasks} />}
    </div>
  );
}

const s = {
  page:           { display:'flex', minHeight:'100vh', background:'#0d141c', fontFamily:'Segoe UI, sans-serif' },
  sidebar:        { width:'240px', background:'#141e29', borderRight:'1px solid #1a2732', display:'flex', flexDirection:'column', padding:'24px 0' },
  logo:           { color:'#eef3f7', fontWeight:'700', fontSize:'16px', padding:'0 20px 32px' },
  navItem:        { color:'#8fa1ae', padding:'12px 20px', cursor:'pointer', fontSize:'14px' },
  navActive:      { color:'#eef3f7', background:'#1a2732', borderRight:'3px solid #edb268' },
  userInfo:       { display:'flex', alignItems:'center', gap:'12px', padding:'20px', borderTop:'1px solid #1a2732', marginTop:'auto' },
  userName:       { color:'#eef3f7', fontSize:'13px', fontWeight:'600' },
  userRole:       { color:'#8fa1ae', fontSize:'11px' },
  main:           { flex:1, padding:'40px' },
  header:         { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'32px' },
  welcome:        { color:'#eef3f7', fontSize:'32px', fontWeight:'700', margin:'0 0 6px' },
  subtitle:       { color:'#8fa1ae', margin:0, fontSize:'15px' },
  dayBadge:       { background:'#1a2732', color:'#edb268', padding:'8px 16px', borderRadius:'20px', fontSize:'13px' },
  newUserBtn:     { background:'#1a2732', color:'#A78BFA', border:'1px solid #4C1D95', padding:'10px 14px', borderRadius:'8px', cursor:'pointer', fontSize:'13px', fontWeight:'600' },
  pwBtn:          { background:'#1a2732', color:'#8fa1ae', border:'1px solid #26343f', padding:'10px 14px', borderRadius:'8px', cursor:'pointer', fontSize:'13px' },
  logoutBtn:      { background:'#e0665a', color:'#fff', border:'none', padding:'10px 20px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  card:           { borderRadius:'18px', padding:'24px', marginBottom:'24px' },
  cardHeader:     { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px' },
  cardTitle:      { color:'#eef3f7', fontSize:'18px', fontWeight:'700', margin:'0 0 4px' },
  cardSubtitle:   { color:'#8fa1ae', fontSize:'13px', margin:0 },
  progressPercent:{ color:'#edb268', fontWeight:'700', fontSize:'20px' },
  progressBar:    { background:'#0d141c', borderRadius:'4px', height:'8px', overflow:'hidden', marginBottom:'12px' },
  progressFill:   { background:'#edb268', height:'100%', borderRadius:'4px', transition:'width .5s' },
  nextMilestone:  { color:'#8fa1ae', fontSize:'13px', margin:0 },
  badge:          { background:'#1a2732', color:'#8fa1ae', padding:'6px 14px', borderRadius:'99px', fontSize:'12px', fontWeight:'600' },
  newTaskBtn:     { background:'#0d1f14', color:'#4caf6d', border:'none', padding:'10px 18px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px' },
  memberRow:      { display:'flex', alignItems:'center', gap:'12px', padding:'14px 0', borderBottom:'1px solid #1a2732' },
  viewBtn:        { background:'#1a2732', color:'#edb268', border:'none', padding:'8px 12px', borderRadius:'8px', cursor:'pointer', fontSize:'16px' },
  resetPwBtn:     { background:'#1a2732', color:'#d9a83e', border:'none', padding:'8px 10px', borderRadius:'8px', cursor:'pointer', fontSize:'14px' },
  deleteBtn:      { background:'#240b08', color:'#e0665a', border:'none', padding:'8px 10px', borderRadius:'8px', cursor:'pointer', fontSize:'14px' },
  taskRow:        { display:'flex', alignItems:'center', gap:'12px', padding:'16px 0', borderBottom:'1px solid #1a2732' },
  taskActive:     { background:'#241a06', margin:'0 -24px', padding:'16px 24px', borderLeft:'3px solid #edb268' },
  checkDone:      { color:'#4caf6d', fontSize:'20px', width:'24px', textAlign:'center' },
  checkOpen:      { color:'#748998', fontSize:'20px', width:'24px', textAlign:'center' },
  doneBadge:      { color:'#4caf6d', fontSize:'13px', fontWeight:'600' },
  activeBadge:    { background:'#1a2732', color:'#edb268', padding:'4px 10px', borderRadius:'6px', fontSize:'12px' },
  openBadge:      { background:'#1a2732', color:'#8fa1ae', padding:'4px 10px', borderRadius:'6px', fontSize:'12px' },
  continueBtn:    { background:'#edb268', color:'#fff', border:'none', padding:'8px 18px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px' },
  startBtn:       { background:'#1a2732', color:'#eef3f7', border:'none', padding:'8px 18px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px' },
};

const m = {
  overlay: { position:'fixed', inset:0, background:'rgba(0,0,0,0.6)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 },
  modal:   { borderRadius:'18px', padding:'32px', width:'100%', maxWidth:'440px', boxSizing:'border-box' },
  header:  { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'24px' },
  close:   { background:'none', border:'none', color:'#8fa1ae', fontSize:'20px', cursor:'pointer' },
  label:   { color:'#8fa1ae', fontSize:'13px', fontWeight:'600', display:'block', marginBottom:'6px' },
  input:   { width:'100%', padding:'12px 16px', background:'#0d141c', border:'1px solid #1a2732', borderRadius:'8px', color:'#eef3f7', fontSize:'14px', outline:'none', marginBottom:'16px', boxSizing:'border-box' },
  btn:     { background:'#edb268', color:'#fff', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  cancel:  { background:'#1a2732', color:'#8fa1ae', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer' },
};
