import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import client from '../api/client';

export default function Tasks() {
  const navigate               = useNavigate();
  const [searchParams]         = useSearchParams();
  const role                   = localStorage.getItem('role');
  const username               = localStorage.getItem('username');
  const myUserId               = localStorage.getItem('user_id');

  // Leader kann Mitarbeiter-Tasks ansehen via URL ?user_id=&name=
  const viewUserId = searchParams.get('user_id') || myUserId;
  const viewName   = searchParams.get('name')    || username;
  const isViewing  = viewUserId !== myUserId;

  const [tasks,         setTasks]         = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [explain,       setExplain]       = useState(null);
  const [explainLoading,setExplainLoading]= useState(false);

  // Neue Aufgabe erstellen – nur für Leader/Verwaltung
  const [showNewTask,   setShowNewTask]   = useState(false);
  const [newTitle,      setNewTitle]      = useState('');
  const [newType,       setNewType]       = useState('Onboarding');
  const [creating,      setCreating]      = useState(false);

  const loadTasks = () => {
    setLoading(true);
    client.get(`/api/tasks?user_id=${viewUserId}`)
      .then(res => setTasks(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadTasks(); }, [viewUserId]);

  const completed = tasks.filter(t => t.is_completed).length;
  const total     = tasks.length;
  const progress  = total > 0 ? Math.round((completed / total) * 100) : 0;

  const handleComplete = async (taskId) => {
    try {
      await client.put(`/api/tasks/${taskId}/complete`);
      loadTasks();
    } catch {
      alert('Fehler beim Abschließen.');
    }
  };

  const handleExplain = async (taskId) => {
    setExplainLoading(true);
    setExplain(null);
    try {
      const res = await client.post(`/api/chat/tasks/${taskId}/explain`);
      setExplain(res.data);
    } catch {
      alert('Fehler beim Laden der Erklärung.');
    } finally {
      setExplainLoading(false);
    }
  };

  const handleCreateTask = async () => {
    if (!newTitle) { alert('Bitte Titel eingeben.'); return; }
    setCreating(true);
    try {
      await client.post('/api/tasks', {
        title:       newTitle,
        task_type:   newType,
        assigned_to: parseInt(viewUserId),
        assigned_by: parseInt(myUserId),
      });
      setNewTitle('');
      setShowNewTask(false);
      loadTasks();
    } catch {
      alert('Fehler beim Erstellen der Aufgabe.');
    } finally {
      setCreating(false);
    }
  };

  const canManage = role === 'Leader' || role === 'Verwaltung';

  return (
    <div className="gx-aurora" style={s.page}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>🤖 OnboardGuide AI</div>
        <nav>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/dashboard')}>📊 Dashboard</div>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/chat')}>💬 Chat-Assistent</div>
          <div className="gx-nav-item" style={{...s.navItem, ...s.navActive}}>☰ Meine Aufgaben</div>
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
        <div style={s.header}>
          <div>
            {isViewing && (
              <button style={s.backBtn} onClick={() => navigate('/dashboard')}>
                ← Zurück zum Dashboard
              </button>
            )}
            <h1 style={s.title}>
              {isViewing ? `Aufgaben von ${viewName}` : 'Meine Aufgaben'}
            </h1>
            <p style={s.subtitle}>Dein Onboarding-Fortschritt</p>
          </div>
          {canManage && (
            <button className="gx-btn" style={s.newBtn} onClick={() => setShowNewTask(!showNewTask)}>
              + Neue Aufgabe
            </button>
          )}
        </div>

        {/* Neue Aufgabe Form */}
        {showNewTask && canManage && (
          <div className="gx-card" style={s.form}>
            <h3 style={{color:'#eef3f7', margin:'0 0 16px'}}>
              Neue Aufgabe für {viewName}
            </h3>
            <input
              className="gx-input"
              style={s.input}
              placeholder="Aufgabentitel"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
            />
            <select className="gx-input" style={s.input} value={newType} onChange={e => setNewType(e.target.value)}>
              <option value="Onboarding">Onboarding</option>
              <option value="Projekt">Projekt</option>
            </select>
            <div style={{display:'flex', gap:'12px'}}>
              <button className="gx-btn" style={s.createBtn} onClick={handleCreateTask} disabled={creating}>
                {creating ? 'Wird erstellt...' : 'Aufgabe erstellen'}
              </button>
              <button className="gx-btn" style={s.cancelBtn} onClick={() => setShowNewTask(false)}>
                Abbrechen
              </button>
            </div>
          </div>
        )}

        {/* Progress */}
        <div className="gx-card gx-card--hover" style={s.progressCard}>
          <div style={s.progressHeader}>
            <span style={s.progressLabel}>Gesamtfortschritt</span>
            <div style={{display:'flex', alignItems:'center', gap:'16px'}}>
              <span style={{color:'#8fa1ae', fontSize:'14px'}}>{completed} von {total} Aufgaben erledigt</span>
              <span style={s.progressPercent}>{progress}% abgeschlossen</span>
            </div>
          </div>
          <div style={s.progressBar}>
            <div style={{...s.progressFill, width:`${progress}%`}} />
          </div>
        </div>

        {/* Tasks */}
        <div className="gx-card" style={s.card}>
          {loading ? (
            <p style={{color:'#8fa1ae'}}>Laden...</p>
          ) : tasks.length === 0 ? (
            <p style={{color:'#8fa1ae'}}>Keine Aufgaben vorhanden.</p>
          ) : tasks.map(task => (
            <div key={task.id} className="gx-row" style={s.taskRow}>
              <span style={task.is_completed ? s.checkDone : s.checkOpen}>
                {task.is_completed ? '✓' : '○'}
              </span>
              <div style={{flex:1}}>
                <span style={{
                  color:          task.is_completed ? '#8fa1ae' : '#eef3f7',
                  textDecoration: task.is_completed ? 'line-through' : 'none',
                  fontSize:'15px', fontWeight:'500'
                }}>
                  {task.title}
                </span>
              </div>
              <span style={{
                ...s.typeBadge,
                background: task.task_type === 'Projekt' ? '#2D1B6E' : '#1a2732',
                color:      task.task_type === 'Projekt' ? '#A78BFA' : '#8fa1ae',
              }}>
                {task.task_type}
              </span>
              {!task.is_completed && (
                <>
                  <button className="gx-btn" style={s.explainBtn} onClick={() => handleExplain(task.id)}>
                    Erklären
                  </button>
                  <button className="gx-btn" style={s.completeBtn} onClick={() => handleComplete(task.id)}>
                    Erledigen
                  </button>
                </>
              )}
              {task.is_completed && <span style={s.doneBadge}>Erledigt</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Explain Modal */}
      {(explain || explainLoading) && (
        <div className="gx-modal-overlay" style={s.modal}>
          <div className="gx-modal" style={s.modalCard}>
            <div style={s.modalHeader}>
              <h2 style={{color:'#eef3f7', margin:0}}>
                {explain ? explain.task_title : 'Erklärung wird geladen...'}
              </h2>
              <button className="gx-btn" style={s.closeBtn} onClick={() => setExplain(null)}>✕</button>
            </div>
            {explainLoading && <p style={{color:'#8fa1ae'}}>Wird generiert...</p>}
            {explain && (
              <>
                <p style={{color:'#8fa1ae', marginBottom:'20px'}}>{explain.explanation.summary}</p>
                <h3 style={{color:'#edb268', marginBottom:'12px'}}>Schritte</h3>
                {explain.explanation.steps.map((step, i) => (
                  <div key={i} style={s.step}>
                    <span style={s.stepNum}>{i+1}</span>
                    <span style={{color:'#eef3f7'}}>{step}</span>
                  </div>
                ))}
                {explain.explanation.tools_and_tips?.length > 0 && (
                  <>
                    <h3 style={{color:'#4caf6d', margin:'20px 0 12px'}}>Tools & Tipps</h3>
                    {explain.explanation.tools_and_tips.map((tip, i) => (
                      <div key={i} style={{color:'#8fa1ae', marginBottom:'8px'}}>💡 {tip}</div>
                    ))}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
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
  header:         { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'24px' },
  backBtn:        { background:'none', border:'none', color:'#8fa1ae', cursor:'pointer', fontSize:'13px', padding:0, marginBottom:'8px', display:'block' },
  title:          { color:'#eef3f7', fontSize:'28px', fontWeight:'700', margin:'0 0 4px' },
  subtitle:       { color:'#8fa1ae', margin:0 },
  newBtn:         { background:'#0d1f14', color:'#4caf6d', border:'none', padding:'12px 20px', borderRadius:'8px', cursor:'pointer', fontWeight:'600', fontSize:'13px', height:'fit-content' },
  form:           { borderRadius:'16px', padding:'24px', marginBottom:'24px', display:'flex', flexDirection:'column', gap:'12px' },
  input:          { padding:'12px 16px', background:'#0d141c', border:'1px solid #1a2732', borderRadius:'8px', color:'#eef3f7', fontSize:'14px', outline:'none' },
  createBtn:      { background:'#0d1f14', color:'#4caf6d', border:'none', padding:'12px 20px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  cancelBtn:      { background:'#1a2732', color:'#8fa1ae', border:'none', padding:'12px 20px', borderRadius:'8px', cursor:'pointer' },
  progressCard:   { borderRadius:'16px', padding:'24px', marginBottom:'24px' },
  progressHeader: { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px' },
  progressLabel:  { color:'#eef3f7', fontWeight:'700', fontSize:'16px' },
  progressPercent:{ color:'#edb268', fontWeight:'700', fontSize:'18px' },
  progressBar:    { background:'#0d141c', borderRadius:'4px', height:'8px', overflow:'hidden' },
  progressFill:   { background:'#edb268', height:'100%', borderRadius:'4px', transition:'width .5s' },
  card:           { borderRadius:'16px', overflow:'hidden' },
  taskRow:        { display:'flex', alignItems:'center', gap:'12px', padding:'16px 20px', borderBottom:'1px solid #1a2732' },
  checkDone:      { color:'#4caf6d', fontSize:'20px', width:'24px' },
  checkOpen:      { color:'#748998', fontSize:'20px', width:'24px' },
  typeBadge:      { padding:'4px 10px', borderRadius:'6px', fontSize:'12px', fontWeight:'600' },
  explainBtn:     { background:'transparent', border:'1px solid #edb268', color:'#edb268', padding:'8px 16px', borderRadius:'8px', cursor:'pointer', fontSize:'13px', fontWeight:'600' },
  completeBtn:    { background:'#0d1f14', color:'#4caf6d', border:'none', padding:'8px 16px', borderRadius:'8px', cursor:'pointer', fontSize:'13px', fontWeight:'600' },
  doneBadge:      { color:'#4caf6d', fontSize:'13px', fontWeight:'600' },
  modal:          { position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 },
  modalCard:      { borderRadius:'18px', padding:'32px', maxWidth:'600px', width:'90%', maxHeight:'80vh', overflowY:'auto' },
  modalHeader:    { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px' },
  closeBtn:       { background:'none', border:'none', color:'#8fa1ae', fontSize:'20px', cursor:'pointer' },
  step:           { display:'flex', gap:'12px', alignItems:'flex-start', marginBottom:'12px' },
  stepNum:        { background:'#edb268', color:'#fff', borderRadius:'50%', width:'24px', height:'24px', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'12px', fontWeight:'700', flexShrink:0 },
};
