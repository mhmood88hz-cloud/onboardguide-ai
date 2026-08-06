import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

// ── Passwort ändern Modal ─────────────────────────────────────────────────
function ChangePwModal({ onClose }) {
  const [oldPw,    setOldPw]    = useState('');
  const [newPw,    setNewPw]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const [msg,      setMsg]      = useState('');

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
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={m.overlay}>
      <div style={m.modal}>
        <div style={m.header}>
          <h2 style={{color:'#E2E8F0', margin:0}}>Passwort ändern</h2>
          <button style={m.close} onClick={onClose}>✕</button>
        </div>
        <label style={m.label}>Aktuelles Passwort</label>
        <input style={m.input} type="password" value={oldPw}
               onChange={e => setOldPw(e.target.value)} />
        <label style={m.label}>Neues Passwort</label>
        <input style={m.input} type="password" value={newPw}
               onChange={e => setNewPw(e.target.value)} />
        {msg && <p style={{color: msg.startsWith('✅') ? '#34D399' : '#EF4444', fontSize:'13px'}}>{msg}</p>}
        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button style={m.btn} onClick={handle} disabled={loading}>
            {loading ? 'Wird gespeichert...' : 'Ändern'}
          </button>
          <button style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Passwort zurücksetzen Modal (Verwaltung) ──────────────────────────────
function ResetPwModal({ member, onClose }) {
  const [newPw,   setNewPw]   = useState('');
  const [loading, setLoading] = useState(false);
  const [msg,     setMsg]     = useState('');

  const handle = async () => {
    if (!newPw) { setMsg('Bitte neues Passwort eingeben.'); return; }
    setLoading(true);
    try {
      await client.post('/api/auth/reset-password', {
        user_id: member.id, new_password: newPw
      });
      setMsg(`✅ Passwort von '${member.username}' zurückgesetzt.`);
      setTimeout(onClose, 1500);
    } catch {
      setMsg('❌ Fehler beim Zurücksetzen.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={m.overlay}>
      <div style={m.modal}>
        <div style={m.header}>
          <h2 style={{color:'#E2E8F0', margin:0}}>Passwort zurücksetzen</h2>
          <button style={m.close} onClick={onClose}>✕</button>
        </div>
        <p style={{color:'#64748B', marginBottom:'16px', fontSize:'14px'}}>
          Neues Passwort für <b style={{color:'#E2E8F0'}}>{member.username}</b>
        </p>
        <label style={m.label}>Neues Passwort</label>
        <input style={m.input} type="password" value={newPw}
               onChange={e => setNewPw(e.target.value)} />
        {msg && <p style={{color: msg.startsWith('✅') ? '#34D399' : '#EF4444', fontSize:'13px'}}>{msg}</p>}
        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button style={m.btn} onClick={handle} disabled={loading}>
            {loading ? 'Wird gesetzt...' : 'Zurücksetzen'}
          </button>
          <button style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Neue Aufgabe Modal ────────────────────────────────────────────────────
function NewTaskModal({ team, onClose, onCreated }) {
  const userId               = localStorage.getItem('user_id');
  const [title,      setTitle]      = useState('');
  const [taskType,   setTaskType]   = useState('Onboarding');
  const [assignedTo, setAssignedTo] = useState('');
  const [loading,    setLoading]    = useState(false);

  const handle = async () => {
    if (!title || !assignedTo) { alert('Bitte alle Felder ausfüllen.'); return; }
    setLoading(true);
    try {
      await client.post('/api/tasks', {
        title,
        task_type:   taskType,
        assigned_to: parseInt(assignedTo),
        assigned_by: parseInt(userId),
      });
      onCreated();
      onClose();
    } catch {
      alert('Fehler beim Erstellen.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={m.overlay}>
      <div style={m.modal}>
        <div style={m.header}>
          <h2 style={{color:'#E2E8F0', margin:0}}>Neue Aufgabe erstellen</h2>
          <button style={m.close} onClick={onClose}>✕</button>
        </div>
        <label style={m.label}>Titel</label>
        <input style={m.input} placeholder="z.B. VPN einrichten"
               value={title} onChange={e => setTitle(e.target.value)} />
        <label style={m.label}>Typ</label>
        <select style={m.input} value={taskType} onChange={e => setTaskType(e.target.value)}>
          <option value="Onboarding">Onboarding</option>
          <option value="Projekt">Projekt</option>
        </select>
        <label style={m.label}>Mitarbeiter</label>
        <select style={m.input} value={assignedTo} onChange={e => setAssignedTo(e.target.value)}>
          <option value="">Bitte auswählen</option>
          {team.map(u => (
            <option key={u.id} value={u.id}>
              {u.username} ({u.department || 'Allgemein'})
            </option>
          ))}
        </select>
        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button style={m.btn} onClick={handle} disabled={loading}>
            {loading ? 'Wird erstellt...' : 'Erstellen'}
          </button>
          <button style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate              = useNavigate();
  const username              = localStorage.getItem('username');
  const role                  = localStorage.getItem('role');
  const userId                = localStorage.getItem('user_id');

  const [tasks,       setTasks]       = useState([]);
  const [team,        setTeam]        = useState([]);
  const [loading,     setLoading]     = useState(true);

  // Modals
  const [showChangePw,  setShowChangePw]  = useState(false);
  const [resetMember,   setResetMember]   = useState(null);
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
        .then(res => setTeam(res.data))
        .catch(err => console.error(err));
    } else if (role === 'Verwaltung') {
      client.get('/api/users')
        .then(res => setTeam(res.data))
        .catch(err => console.error(err));
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
    } catch {
      alert('Fehler beim Löschen.');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const canManageTeam = role === 'Leader' || role === 'Verwaltung';

  return (
    <div style={s.page}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>🤖 OnboardGuide AI</div>
        <nav>
          <div style={{...s.navItem, ...s.navActive}}>📊 Dashboard</div>
          <div style={s.navItem} onClick={() => navigate('/chat')}>💬 Chat-Assistent</div>
          <div style={s.navItem} onClick={() => navigate('/tasks')}>☰ Meine Aufgaben</div>
          {role === 'Verwaltung' && (
            <div style={s.navItem} onClick={() => navigate('/documents')}>📄 Dokumente</div>
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
        {/* Header */}
        <div style={s.header}>
          <div>
            <h1 style={s.welcome}>Willkommen zurück, {username}! 👋</h1>
            <p style={s.subtitle}>Lass uns da weitermachen, wo du aufgehört hast.</p>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
            <div style={s.dayBadge}>📅 Onboarding läuft</div>
            <button style={s.pwBtn} onClick={() => setShowChangePw(true)}>🔑 Passwort</button>
            <button style={s.logoutBtn} onClick={handleLogout}>Ausloggen</button>
          </div>
        </div>

        {/* Progress Card */}
        <div style={s.card}>
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
              <span style={{color:'#7DD3FC', fontWeight:'600'}}>{next.title}</span>
            </p>
          )}
        </div>

        {/* Team Block – Leader + Verwaltung */}
        {canManageTeam && (
          <div style={s.card}>
            <div style={s.cardHeader}>
              <div>
                <h2 style={s.cardTitle}>
                  {role === 'Verwaltung' ? 'Alle Benutzer' : 'Mein Team'}
                </h2>
                <p style={s.cardSubtitle}>{team.length} Mitarbeiter</p>
              </div>
              <button style={s.newTaskBtn} onClick={() => setShowNewTask(true)}>
                + Neue Aufgabe
              </button>
            </div>

            {team.length === 0 ? (
              <p style={{color:'#64748B'}}>Keine Mitarbeiter gefunden.</p>
            ) : team.map(member => {
              const p = member.progress_percent || 0;
              const col = p >= 75 ? '#34D399' : p >= 40 ? '#1E40AF' : '#F59E0B';
              return (
                <div key={member.id} style={s.memberRow}>
                  <span style={{fontSize:'24px'}}>👤</span>
                  <div style={{flex:1}}>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'6px'}}>
                      <div>
                        <span style={{color:'#E2E8F0', fontWeight:'600', fontSize:'14px'}}>
                          {member.username}
                        </span>
                        <span style={{color:'#64748B', fontSize:'12px', marginLeft:'8px'}}>
                          {member.department || 'Allgemein'} · {member.user_role}
                        </span>
                      </div>
                      <span style={{color:col, fontWeight:'700', fontSize:'14px'}}>{p}%</span>
                    </div>
                    <div style={s.progressBar}>
                      <div style={{...s.progressFill, width:`${p}%`, background:col}} />
                    </div>
                  </div>

                  {/* Aktionen */}
                  <div style={{display:'flex', gap:'6px'}}>
                    <button
                      style={s.viewBtn}
                      onClick={() => navigate(`/tasks?user_id=${member.id}&name=${member.username}`)}
                      title="Aufgaben anzeigen"
                    >
                      →
                    </button>
                    <button
                      style={s.resetPwBtn}
                      onClick={() => setResetMember(member)}
                      title="Passwort zurücksetzen"
                    >
                      🔑
                    </button>
                    {role === 'Verwaltung' && (
                      <button
                        style={s.deleteBtn}
                        onClick={() => handleDelete(member.id, member.username)}
                        title="Benutzer löschen"
                      >
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
        <div style={s.card}>
          <div style={s.cardHeader}>
            <h2 style={s.cardTitle}>Deine Aufgaben</h2>
            <span style={s.badge}>{total - completed} verbleibend</span>
          </div>

          {loading ? (
            <p style={{color:'#64748B', padding:'16px 0'}}>Laden...</p>
          ) : tasks.length === 0 ? (
            <p style={{color:'#64748B', padding:'16px 0'}}>Keine Aufgaben vorhanden.</p>
          ) : (
            tasks.slice(0, 5).map(task => (
              <div key={task.id} style={{
                ...s.taskRow,
                ...(task === next ? s.taskActive : {}),
              }}>
                <span style={task.is_completed ? s.checkDone : s.checkOpen}>
                  {task.is_completed ? '✓' : '○'}
                </span>
                <div style={{flex:1}}>
                  <div style={{
                    color: task.is_completed ? '#64748B' : '#E2E8F0',
                    textDecoration: task.is_completed ? 'line-through' : 'none',
                    fontWeight:'500', fontSize:'15px',
                  }}>
                    {task.title}
                  </div>
                  {task === next && (
                    <div style={{color:'#64748B', fontSize:'12px', marginTop:'2px'}}>
                      {task.task_type}
                    </div>
                  )}
                </div>
                {task.is_completed && <span style={s.doneBadge}>erledigt</span>}
                {!task.is_completed && task === next && (
                  <>
                    <span style={s.activeBadge}>in Bearbeitung</span>
                    <button style={s.continueBtn} onClick={() => navigate('/tasks')}>Fortsetzen</button>
                  </>
                )}
                {!task.is_completed && task !== next && (
                  <>
                    <span style={s.openBadge}>offen</span>
                    <button style={s.startBtn} onClick={() => navigate('/tasks')}>Starten</button>
                  </>
                )}
              </div>
            ))
          )}
          {tasks.length > 5 && (
            <div style={{padding:'14px 0', color:'#1E40AF', cursor:'pointer', fontSize:'14px', textAlign:'center'}}
                 onClick={() => navigate('/tasks')}>
              Alle {tasks.length} Aufgaben anzeigen →
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showChangePw && <ChangePwModal onClose={() => setShowChangePw(false)} />}
      {resetMember  && <ResetPwModal  member={resetMember} onClose={() => setResetMember(null)} />}
      {showNewTask  && (
        <NewTaskModal
          team={team}
          onClose={() => setShowNewTask(false)}
          onCreated={loadTasks}
        />
      )}
    </div>
  );
}

const s = {
  page:           { display:'flex', minHeight:'100vh', background:'#0A0E18', fontFamily:'Segoe UI, sans-serif' },
  sidebar:        { width:'240px', background:'#10192B', borderRight:'1px solid #1E293B', display:'flex', flexDirection:'column', padding:'24px 0' },
  logo:           { color:'#E2E8F0', fontWeight:'700', fontSize:'16px', padding:'0 20px 32px' },
  navItem:        { color:'#64748B', padding:'12px 20px', cursor:'pointer', fontSize:'14px' },
  navActive:      { color:'#E2E8F0', background:'#1E293B', borderRight:'3px solid #1E40AF' },
  userInfo:       { display:'flex', alignItems:'center', gap:'12px', padding:'20px', borderTop:'1px solid #1E293B', marginTop:'auto' },
  userName:       { color:'#E2E8F0', fontSize:'13px', fontWeight:'600' },
  userRole:       { color:'#64748B', fontSize:'11px' },
  main:           { flex:1, padding:'40px' },
  header:         { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'32px' },
  welcome:        { color:'#E2E8F0', fontSize:'32px', fontWeight:'700', margin:'0 0 6px' },
  subtitle:       { color:'#64748B', margin:0, fontSize:'15px' },
  dayBadge:       { background:'#1E293B', color:'#7DD3FC', padding:'8px 16px', borderRadius:'20px', fontSize:'13px' },
  pwBtn:          { background:'#1E293B', color:'#94A3B8', border:'1px solid #334155', padding:'10px 14px', borderRadius:'8px', cursor:'pointer', fontSize:'13px' },
  logoutBtn:      { background:'#EF4444', color:'#fff', border:'none', padding:'10px 20px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  card:           { background:'#10192B', border:'1px solid #1E293B', borderRadius:'12px', padding:'24px', marginBottom:'24px' },
  cardHeader:     { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px' },
  cardTitle:      { color:'#E2E8F0', fontSize:'18px', fontWeight:'700', margin:'0 0 4px' },
  cardSubtitle:   { color:'#64748B', fontSize:'13px', margin:0 },
  progressPercent:{ color:'#1E40AF', fontWeight:'700', fontSize:'20px' },
  progressBar:    { background:'#0A0E18', borderRadius:'4px', height:'8px', overflow:'hidden', marginBottom:'12px' },
  progressFill:   { background:'#1E40AF', height:'100%', borderRadius:'4px', transition:'width .5s' },
  nextMilestone:  { color:'#64748B', fontSize:'13px', margin:0 },
  badge:          { background:'#1E293B', color:'#64748B', padding:'6px 14px', borderRadius:'99px', fontSize:'12px', fontWeight:'600' },
  newTaskBtn:     { background:'#065F46', color:'#34D399', border:'none', padding:'10px 18px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px' },
  memberRow:      { display:'flex', alignItems:'center', gap:'12px', padding:'14px 0', borderBottom:'1px solid #1E293B' },
  viewBtn:        { background:'#1E293B', color:'#7DD3FC', border:'none', padding:'8px 12px', borderRadius:'8px', cursor:'pointer', fontSize:'16px' },
  resetPwBtn:     { background:'#1E293B', color:'#F59E0B', border:'none', padding:'8px 10px', borderRadius:'8px', cursor:'pointer', fontSize:'14px' },
  deleteBtn:      { background:'#3B0000', color:'#EF4444', border:'none', padding:'8px 10px', borderRadius:'8px', cursor:'pointer', fontSize:'14px' },
  taskRow:        { display:'flex', alignItems:'center', gap:'12px', padding:'16px 0', borderBottom:'1px solid #1E293B' },
  taskActive:     { background:'#0D1F3C', margin:'0 -24px', padding:'16px 24px', borderLeft:'3px solid #1E40AF' },
  checkDone:      { color:'#34D399', fontSize:'20px', width:'24px', textAlign:'center' },
  checkOpen:      { color:'#475569', fontSize:'20px', width:'24px', textAlign:'center' },
  doneBadge:      { color:'#34D399', fontSize:'13px', fontWeight:'600' },
  activeBadge:    { background:'#1E293B', color:'#7DD3FC', padding:'4px 10px', borderRadius:'6px', fontSize:'12px' },
  openBadge:      { background:'#1E293B', color:'#64748B', padding:'4px 10px', borderRadius:'6px', fontSize:'12px' },
  continueBtn:    { background:'#1E40AF', color:'#fff', border:'none', padding:'8px 18px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px' },
  startBtn:       { background:'#1E293B', color:'#E2E8F0', border:'none', padding:'8px 18px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px' },
};

const m = {
  overlay: { position:'fixed', inset:0, background:'rgba(0,0,0,0.75)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 },
  modal:   { background:'#10192B', border:'1px solid #1E293B', borderRadius:'16px', padding:'32px', width:'420px', boxSizing:'border-box' },
  header:  { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'24px' },
  close:   { background:'none', border:'none', color:'#64748B', fontSize:'20px', cursor:'pointer' },
  label:   { color:'#94A3B8', fontSize:'13px', fontWeight:'600', display:'block', marginBottom:'6px' },
  input:   { width:'100%', padding:'12px 16px', background:'#0A0E18', border:'1px solid #1E293B', borderRadius:'8px', color:'#E2E8F0', fontSize:'14px', outline:'none', marginBottom:'16px', boxSizing:'border-box' },
  btn:     { background:'#1E40AF', color:'#fff', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  cancel:  { background:'#1E293B', color:'#64748B', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer' },
};
