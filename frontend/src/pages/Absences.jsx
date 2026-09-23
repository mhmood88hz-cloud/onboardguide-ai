import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

const todayStr = () => new Date().toISOString().slice(0, 10);

// ── Krank melden / Urlaub beantragen Modal ────────────────────────────────
function LeaveModal({ type, onClose, onCreated }) {
  const isSick = type === 'sick';
  const [startDate, setStartDate] = useState(todayStr());
  const [endDate,   setEndDate]   = useState(todayStr());
  const [reason,    setReason]    = useState('');
  const [loading,   setLoading]   = useState(false);
  const [msg,       setMsg]       = useState('');

  const handle = async () => {
    if (endDate < startDate) { setMsg('❌ Enddatum darf nicht vor Startdatum liegen.'); return; }
    setLoading(true);
    try {
      await client.post(`/api/leave/${isSick ? 'sick' : 'vacation'}`, {
        start_date: startDate, end_date: endDate, reason: reason.trim() || null,
      });
      setMsg(isSick
        ? '✅ Krankmeldung erfasst.'
        : '✅ Urlaubsantrag eingereicht – wartet auf Bestätigung.');
      setTimeout(() => { onCreated(); onClose(); }, 1200);
    } catch (err) {
      setMsg('❌ ' + (err.response?.data?.detail || 'Fehler beim Senden.'));
    } finally { setLoading(false); }
  };

  return (
    <div className="gx-modal-overlay" style={m.overlay}>
      <div className="gx-modal" style={m.modal}>
        <div style={m.header}>
          <h2 style={{color:'#eef3f7', margin:0}}>{isSick ? 'Krank melden' : 'Urlaub beantragen'}</h2>
          <button className="gx-btn" style={m.close} onClick={onClose}>✕</button>
        </div>

        {!isSick && (
          <p style={{color:'#8fa1ae', fontSize:'13px', marginTop:0}}>
            Der Antrag muss von deinem Leader oder der Verwaltung bestätigt werden,
            bevor er im System als Urlaub gilt.
          </p>
        )}

        <label style={m.label}>Von</label>
        <input className="gx-input" style={m.input} type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />

        <label style={m.label}>Bis</label>
        <input className="gx-input" style={m.input} type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />

        <label style={m.label}>Grund (optional)</label>
        <textarea className="gx-input" style={{...m.input, height:'70px', resize:'vertical'}}
                  value={reason} onChange={e => setReason(e.target.value)} />

        {msg && <p style={{color: msg.startsWith('✅') ? '#4caf6d' : '#e0665a', fontSize:'13px'}}>{msg}</p>}

        <div style={{display:'flex', gap:'12px', marginTop:'8px'}}>
          <button className="gx-btn" style={m.btn} onClick={handle} disabled={loading}>
            {loading ? 'Wird gesendet...' : isSick ? 'Krankmeldung senden' : 'Antrag stellen'}
          </button>
          <button className="gx-btn" style={m.cancel} onClick={onClose}>Abbrechen</button>
        </div>
      </div>
    </div>
  );
}

// ── Abwesenheiten ──────────────────────────────────────────────────────────
export default function Absences() {
  const navigate  = useNavigate();
  const username  = localStorage.getItem('username');
  const role      = localStorage.getItem('role');
  const isManager = role === 'Leader' || role === 'Verwaltung';

  const [mine,    setMine]    = useState([]);
  const [pending, setPending] = useState([]);
  const [presence,        setPresence]        = useState([]);
  const [presenceDate,    setPresenceDate]    = useState(todayStr());
  const [presenceLoading, setPresenceLoading] = useState(false);
  const [filter,          setFilter]          = useState('');
  const [modalType,       setModalType]       = useState(null);

  const loadMine = () => {
    client.get('/api/leave/mine').then(res => setMine(res.data)).catch(console.error);
  };
  const loadPending = () => {
    if (!isManager) return;
    client.get('/api/leave/pending').then(res => setPending(res.data)).catch(console.error);
  };
  const loadPresence = (d) => {
    if (!isManager) return;
    setPresenceLoading(true);
    client.get(`/api/leave/team-presence?on_date=${d || presenceDate}`)
      .then(res => setPresence(res.data))
      .catch(console.error)
      .finally(() => setPresenceLoading(false));
  };

  useEffect(() => { loadMine(); loadPending(); loadPresence(todayStr()); }, []);

  const refreshAll = () => { loadMine(); loadPending(); loadPresence(); };

  const handleApprove = async (id) => {
    try { await client.put(`/api/leave/${id}/approve`); refreshAll(); }
    catch (err) { alert(err.response?.data?.detail || 'Fehler beim Bestätigen.'); }
  };

  const handleReject = async (id) => {
    if (!window.confirm('Antrag wirklich ablehnen?')) return;
    try { await client.put(`/api/leave/${id}/reject`); loadPending(); }
    catch (err) { alert(err.response?.data?.detail || 'Fehler beim Ablehnen.'); }
  };

  const statusBadge = (status) => {
    if (status === 'Genehmigt') return <span style={{...s.badge, color:'#4caf6d', borderColor:'#0d1f14'}}>Genehmigt</span>;
    if (status === 'Abgelehnt') return <span style={{...s.badge, color:'#e0665a', borderColor:'#240b08'}}>Abgelehnt</span>;
    return <span style={{...s.badge, color:'#d9a83e', borderColor:'#241a06'}}>Ausstehend</span>;
  };

  const filteredPresence = presence.filter(p =>
    p.username.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="gx-aurora" style={s.page}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>🤖 OnboardGuide AI</div>
        <nav>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/dashboard')}>📊 Dashboard</div>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/chat')}>💬 Chat-Assistent</div>
          <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/tasks')}>☰ Meine Aufgaben</div>
          {role === 'Verwaltung' && (
            <div className="gx-nav-item" style={s.navItem} onClick={() => navigate('/documents')}>📄 Dokumente</div>
          )}
          <div className="gx-nav-item" style={{...s.navItem, ...s.navActive}}>🌴 Abwesenheiten</div>
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
            <h1 style={s.title}>Abwesenheiten</h1>
            <p style={s.subtitle}>Krankmeldungen &amp; Urlaub verwalten</p>
          </div>
          <div style={{display:'flex', gap:'10px'}}>
            <button className="gx-btn" style={s.sickBtn} onClick={() => setModalType('sick')}>🤒 Krank melden</button>
            <button className="gx-btn" style={s.vacBtn} onClick={() => setModalType('vacation')}>🏖️ Urlaub beantragen</button>
          </div>
        </div>

        {/* Team-Anwesenheit – nur Leader/Verwaltung */}
        {isManager && (
          <div className="gx-card gx-card--hover" style={s.card}>
            <div style={s.cardHeader}>
              <div>
                <h2 style={s.cardTitle}>Team-Anwesenheit</h2>
                <p style={s.cardSubtitle}>Wer ist am gewählten Tag anwesend?</p>
              </div>
              <input className="gx-input" style={s.dateInput} type="date" value={presenceDate}
                     onChange={e => { setPresenceDate(e.target.value); loadPresence(e.target.value); }} />
            </div>

            <input className="gx-input" style={s.filterInput} placeholder="🔍 Mitarbeiter suchen..."
                   value={filter} onChange={e => setFilter(e.target.value)} />

            {presenceLoading ? (
              <p style={{color:'#8fa1ae'}}>Laden...</p>
            ) : filteredPresence.length === 0 ? (
              <p style={{color:'#8fa1ae'}}>Keine Teammitglieder gefunden.</p>
            ) : filteredPresence.map(p => (
              <div key={p.user_id} className="gx-row" style={s.presenceRow}>
                <span style={{fontSize:'20px'}}>
                  {p.on_leave ? (p.leave_type === 'Krankmeldung' ? '🤒' : '🏖️') : '✅'}
                </span>
                <div style={{flex:1}}>
                  <div style={{color:'#eef3f7', fontWeight:'600', fontSize:'14px'}}>
                    {p.username}
                    <span style={{color:'#8fa1ae', fontWeight:'400', fontSize:'12px'}}>
                      {' '}· {p.department || 'Allgemein'}
                    </span>
                  </div>
                  {p.on_leave ? (
                    <div style={{color:'#d9a83e', fontSize:'12px', marginTop:'2px'}}>
                      {p.leave_type}
                      {p.substitute_username
                        ? <span style={{color:'#edb268'}}> · Vertretung: {p.substitute_username}</span>
                        : <span style={{color:'#e0665a'}}> · keine Vertretung gefunden</span>}
                    </div>
                  ) : (
                    <div style={{color:'#4caf6d', fontSize:'12px', marginTop:'2px'}}>Anwesend</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Offene Urlaubsanträge – nur Leader/Verwaltung */}
        {isManager && (
          <div className="gx-card gx-card--hover" style={s.card}>
            <div style={s.cardHeader}>
              <div>
                <h2 style={s.cardTitle}>Offene Urlaubsanträge</h2>
                <p style={s.cardSubtitle}>{pending.length} wartend auf Bestätigung</p>
              </div>
            </div>
            {pending.length === 0 ? (
              <p style={{color:'#8fa1ae'}}>Keine offenen Anträge.</p>
            ) : pending.map(req => (
              <div key={req.id} className="gx-row" style={s.requestRow}>
                <span style={{fontSize:'20px'}}>🏖️</span>
                <div style={{flex:1}}>
                  <div style={{color:'#eef3f7', fontWeight:'600', fontSize:'14px'}}>{req.username}</div>
                  <div style={{color:'#8fa1ae', fontSize:'12px', marginTop:'2px'}}>
                    {req.start_date} – {req.end_date}{req.reason ? ` · ${req.reason}` : ''}
                  </div>
                </div>
                <button className="gx-btn" style={s.approveBtn} onClick={() => handleApprove(req.id)}>✓ Bestätigen</button>
                <button className="gx-btn" style={s.rejectBtn} onClick={() => handleReject(req.id)}>✕ Ablehnen</button>
              </div>
            ))}
          </div>
        )}

        {/* Meine Abwesenheiten */}
        <div className="gx-card gx-card--hover" style={s.card}>
          <div style={s.cardHeader}>
            <h2 style={s.cardTitle}>Meine Abwesenheiten</h2>
          </div>
          {mine.length === 0 ? (
            <p style={{color:'#8fa1ae'}}>Noch keine Meldungen.</p>
          ) : mine.map(req => (
            <div key={req.id} className="gx-row" style={s.requestRow}>
              <span style={{fontSize:'20px'}}>{req.leave_type === 'Krankmeldung' ? '🤒' : '🏖️'}</span>
              <div style={{flex:1}}>
                <div style={{color:'#eef3f7', fontWeight:'600', fontSize:'14px'}}>{req.leave_type}</div>
                <div style={{color:'#8fa1ae', fontSize:'12px', marginTop:'2px'}}>
                  {req.start_date} – {req.end_date}{req.reason ? ` · ${req.reason}` : ''}
                  {req.substitute_username && ` · Vertretung: ${req.substitute_username}`}
                </div>
              </div>
              {statusBadge(req.status)}
            </div>
          ))}
        </div>
      </div>

      {modalType && (
        <LeaveModal type={modalType} onClose={() => setModalType(null)} onCreated={refreshAll} />
      )}
    </div>
  );
}

const s = {
  page:         { display:'flex', minHeight:'100vh', background:'#0d141c', fontFamily:'Segoe UI, sans-serif' },
  sidebar:      { width:'240px', background:'#141e29', borderRight:'1px solid #1a2732', display:'flex', flexDirection:'column', padding:'24px 0' },
  logo:         { color:'#eef3f7', fontWeight:'700', fontSize:'16px', padding:'0 20px 32px' },
  navItem:      { color:'#8fa1ae', padding:'12px 20px', cursor:'pointer', fontSize:'14px' },
  navActive:    { color:'#eef3f7', background:'#1a2732', borderRight:'3px solid #edb268' },
  userInfo:     { display:'flex', alignItems:'center', gap:'12px', padding:'20px', borderTop:'1px solid #1a2732', marginTop:'auto' },
  userName:     { color:'#eef3f7', fontSize:'13px', fontWeight:'600' },
  userRole:     { color:'#8fa1ae', fontSize:'11px' },
  main:         { flex:1, padding:'40px' },
  header:       { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'24px', flexWrap:'wrap', gap:'16px' },
  title:        { color:'#eef3f7', fontSize:'28px', fontWeight:'700', margin:'0 0 4px' },
  subtitle:     { color:'#8fa1ae', margin:0, fontSize:'14px' },
  sickBtn:      { background:'#1a2732', color:'#d9a83e', border:'1px solid #d9a83e', borderRadius:'8px', padding:'12px 18px', cursor:'pointer', fontSize:'13px', fontWeight:'600' },
  vacBtn:       { background:'#0d1f14', color:'#4caf6d', border:'none', borderRadius:'8px', padding:'12px 18px', cursor:'pointer', fontSize:'13px', fontWeight:'600' },
  card:         { borderRadius:'16px', padding:'24px', marginBottom:'24px' },
  cardHeader:   { display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'16px', flexWrap:'wrap', gap:'12px' },
  cardTitle:    { color:'#eef3f7', fontSize:'18px', fontWeight:'700', margin:'0 0 4px' },
  cardSubtitle: { color:'#8fa1ae', fontSize:'13px', margin:0 },
  dateInput:    { padding:'10px 14px', background:'#0d141c', border:'1px solid #1a2732', borderRadius:'8px', color:'#eef3f7', fontSize:'13px', outline:'none' },
  filterInput:  { width:'100%', padding:'10px 14px', background:'#0d141c', border:'1px solid #1a2732', borderRadius:'8px', color:'#eef3f7', fontSize:'13px', outline:'none', marginBottom:'14px', boxSizing:'border-box' },
  presenceRow:  { display:'flex', alignItems:'center', gap:'12px', padding:'12px 0', borderBottom:'1px solid #1a2732' },
  requestRow:   { display:'flex', alignItems:'center', gap:'12px', padding:'14px 0', borderBottom:'1px solid #1a2732' },
  badge:        { border:'1px solid', borderRadius:'6px', padding:'4px 10px', fontSize:'11px', fontWeight:'700' },
  approveBtn:   { background:'#0d1f14', color:'#4caf6d', border:'none', padding:'8px 14px', borderRadius:'8px', cursor:'pointer', fontSize:'12px', fontWeight:'600' },
  rejectBtn:    { background:'#240b08', color:'#e0665a', border:'none', padding:'8px 14px', borderRadius:'8px', cursor:'pointer', fontSize:'12px', fontWeight:'600' },
};

const m = {
  overlay: { position:'fixed', inset:0, background:'rgba(0,0,0,0.75)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 },
  modal:   { borderRadius:'18px', padding:'32px', width:'100%', maxWidth:'440px', boxSizing:'border-box' },
  header:  { display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px' },
  close:   { background:'none', border:'none', color:'#8fa1ae', fontSize:'20px', cursor:'pointer' },
  label:   { color:'#8fa1ae', fontSize:'13px', fontWeight:'600', display:'block', marginBottom:'6px' },
  input:   { width:'100%', padding:'12px 16px', background:'#0d141c', border:'1px solid #1a2732', borderRadius:'8px', color:'#eef3f7', fontSize:'14px', outline:'none', marginBottom:'16px', boxSizing:'border-box' },
  btn:     { background:'#edb268', color:'#fff', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer', fontWeight:'600' },
  cancel:  { background:'#1a2732', color:'#8fa1ae', border:'none', padding:'12px 24px', borderRadius:'8px', cursor:'pointer' },
};
