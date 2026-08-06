import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function Chat() {
  const navigate               = useNavigate();
  const username               = localStorage.getItem('username');
  const role                   = localStorage.getItem('role');
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading,  setLoading]  = useState(false);
  const [histLoading, setHistLoading] = useState(true);
  const bottomRef               = useRef(null);

  // Gesprächsverlauf beim Öffnen laden
  useEffect(() => {
    client.get('/api/chat/history')
      .then(res => {
        const history = res.data.flatMap(msg => [
          { role: 'user', text: msg.user_question },
          { role: 'ai',   text: msg.ai_response, sources: [], comparison: [] }
        ]);
        setMessages(history);
      })
      .catch(err => console.error(err))
      .finally(() => setHistLoading(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (compare = false) => {
    if (!question.trim() || loading) return;
    const q = question.trim();
    setQuestion('');
    setMessages(prev => [...prev, {
      role: 'user', text: q, isCompare: compare
    }]);
    setLoading(true);

    try {
      const res = await client.post('/api/chat/ask', {
        question:       q,
        compare_models: compare,
      });
      setMessages(prev => [...prev, {
        role:       'ai',
        text:       res.data.ai_response,
        sources:    res.data.chunk_stats      || [],
        comparison: res.data.model_comparison || [],
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'ai',
        text: 'Fehler beim Abrufen der Antwort. Bitte versuche es erneut.',
        sources: [], comparison: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={s.page}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.logo}>🤖 OnboardGuide AI</div>
        <nav>
          <div style={s.navItem} onClick={() => navigate('/dashboard')}>📊 Dashboard</div>
          <div style={{...s.navItem, ...s.navActive}}>💬 Chat-Assistent</div>
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
            <h1 style={s.title}>Chat-Assistent</h1>
            <p style={s.subtitle}>Frag mich alles zu deinem Onboarding</p>
          </div>
          <div style={s.dayBadge}>📅 Tag 2 im Onboarding</div>
        </div>

        {/* Messages */}
        <div style={s.messages}>
          {histLoading && (
            <p style={{color:'#475569', textAlign:'center'}}>Verlauf wird geladen...</p>
          )}

          {!histLoading && messages.length === 0 && (
            <div style={s.empty}>
              <div style={{fontSize:'48px', marginBottom:'16px'}}>💬</div>
              <p style={{color:'#64748B', fontSize:'15px'}}>
                Stelle deine erste Frage zum Onboarding
              </p>
              <p style={{color:'#475569', fontSize:'13px', marginTop:'8px'}}>
                Tipp: Nutze ⚡ Vergleichen um zwei KI-Modelle zu vergleichen
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i}>
              {/* User Message */}
              {msg.role === 'user' && (
                <div style={s.userRow}>
                  <div style={s.userBubble}>
                    {msg.text}
                    {msg.isCompare && (
                      <span style={s.compareBadge}>⚡ Modellvergleich</span>
                    )}
                  </div>
                </div>
              )}

              {/* AI Message */}
              {msg.role === 'ai' && (
                <div style={s.aiRow}>
                  <div style={s.aiAvatar}>🤖</div>
                  <div style={{flex:1}}>
                    <div style={s.aiBubble}>
                      <p style={{margin:0, whiteSpace:'pre-wrap', lineHeight:'1.7'}}>
                        {msg.text}
                      </p>
                    </div>

                    {/* RAG Similarity Scores */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div style={s.sourcesBox}>
                        <div style={s.sourcesLabel}>📊 QUELLENANGABEN</div>
                        <div style={{display:'flex', gap:'12px', flexWrap:'wrap'}}>
                          {msg.sources.map((src, j) => {
                            const pct = Math.round(src.similarity_score * 100);
                            const col = pct > 60 ? '#34D399' : pct > 40 ? '#F59E0B' : '#94A3B8';
                            return (
                              <div key={j} style={s.sourceCard}>
                                <div style={{display:'flex', alignItems:'center', gap:'6px', marginBottom:'6px'}}>
                                  <span>📄</span>
                                  <span style={{color:'#E2E8F0', fontSize:'12px', fontWeight:'600'}}>
                                    {(src.document || '').substring(0, 22)}...
                                  </span>
                                </div>
                                <div style={s.scoreBarWrap}>
                                  <div style={{...s.scoreBarFill, width:`${pct}%`, background:col}} />
                                </div>
                                <span style={{color:col, fontSize:'12px', fontWeight:'700'}}>
                                  {pct}%
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Model Comparison */}
                    {msg.comparison && msg.comparison.length > 0 && (
                      <div style={s.sourcesBox}>
                        <div style={s.sourcesLabel}>⚡ MODEL COMPARISON</div>
                        <div style={{display:'flex', gap:'12px'}}>
                          {msg.comparison.map((m, j) => {
                            const col     = m.model === 'gpt-4o-mini' ? '#34D399' : '#F59E0B';
                            const fastest = msg.comparison.reduce((a,b) =>
                              a.response_time <= b.response_time ? a : b
                            ).model;
                            return (
                              <div key={j} style={{...s.compCard, borderColor:col}}>
                                <div style={{color:col, fontWeight:'700', fontSize:'12px', marginBottom:'8px'}}>
                                  {m.model} {m.model === fastest ? '🏆' : ''}
                                </div>
                                <div style={{fontSize:'11px', color:'#94A3B8', lineHeight:'2'}}>
                                  ⏱ <b style={{color:'#E2E8F0'}}>{m.response_time}s</b><br/>
                                  🔢 <b style={{color:'#E2E8F0'}}>{m.tokens_used} tokens</b><br/>
                                  💰 <b style={{color:'#E2E8F0'}}>${m.cost_usd}</b><br/>
                                  📝 <b style={{color:'#E2E8F0'}}>{m.answer_length} chars</b>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={s.aiRow}>
              <div style={s.aiAvatar}>🤖</div>
              <div style={s.aiBubble}>
                <p style={{margin:0, color:'#64748B'}}>Antwort wird generiert...</p>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input Area */}
        <div style={s.inputArea}>
          <input
            style={s.input}
            placeholder="Stelle eine Frage..."
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage(false)}
          />
          <button
            style={s.compareBtn}
            onClick={() => sendMessage(true)}
            disabled={loading}
            title="Beide Modelle vergleichen"
          >
            ⚡ Vergleichen
          </button>
          <button
            style={s.sendBtn}
            onClick={() => sendMessage(false)}
            disabled={loading}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}

const s = {
  page:         { display:'flex', minHeight:'100vh', background:'#0A0E18', fontFamily:'Segoe UI, sans-serif' },
  sidebar:      { width:'240px', background:'#10192B', borderRight:'1px solid #1E293B', display:'flex', flexDirection:'column', padding:'24px 0' },
  logo:         { color:'#E2E8F0', fontWeight:'700', fontSize:'16px', padding:'0 20px 32px' },
  navItem:      { color:'#64748B', padding:'12px 20px', cursor:'pointer', fontSize:'14px' },
  navActive:    { color:'#E2E8F0', background:'#1E293B', borderRight:'3px solid #1E40AF' },
  userInfo:     { display:'flex', alignItems:'center', gap:'12px', padding:'20px', borderTop:'1px solid #1E293B', marginTop:'auto' },
  userName:     { color:'#E2E8F0', fontSize:'13px', fontWeight:'600' },
  userRole:     { color:'#64748B', fontSize:'11px' },
  main:         { flex:1, display:'flex', flexDirection:'column', height:'100vh' },
  header:       { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'28px 40px 20px', borderBottom:'1px solid #1E293B' },
  title:        { color:'#E2E8F0', fontSize:'28px', fontWeight:'700', margin:'0 0 4px' },
  subtitle:     { color:'#64748B', margin:0, fontSize:'14px' },
  dayBadge:     { background:'#1E293B', color:'#7DD3FC', padding:'8px 16px', borderRadius:'20px', fontSize:'13px' },
  messages:     { flex:1, overflowY:'auto', padding:'28px 40px', display:'flex', flexDirection:'column', gap:'24px' },
  empty:        { textAlign:'center', marginTop:'80px' },
  userRow:      { display:'flex', justifyContent:'flex-end' },
  userBubble:   { background:'#1E293B', color:'#E2E8F0', padding:'14px 18px', borderRadius:'16px 16px 4px 16px', maxWidth:'60%', fontSize:'14px', lineHeight:'1.6' },
  compareBadge: { display:'inline-block', marginLeft:'10px', background:'#2D1B00', color:'#F59E0B', padding:'2px 8px', borderRadius:'4px', fontSize:'11px', fontWeight:'600' },
  aiRow:        { display:'flex', gap:'12px', alignItems:'flex-start' },
  aiAvatar:     { fontSize:'28px', marginTop:'4px', flexShrink:0 },
  aiBubble:     { background:'#10192B', border:'1px solid #1E293B', color:'#E2E8F0', padding:'16px 20px', borderRadius:'4px 16px 16px 16px', flex:1, fontSize:'14px', lineHeight:'1.6' },
  sourcesBox:   { marginTop:'12px' },
  sourcesLabel: { color:'#475569', fontSize:'10px', fontWeight:'700', letterSpacing:'1px', marginBottom:'8px' },
  sourceCard:   { background:'#10192B', border:'1px solid #1E293B', borderRadius:'8px', padding:'10px', minWidth:'180px' },
  scoreBarWrap: { background:'#0A0E18', borderRadius:'4px', height:'6px', overflow:'hidden', marginBottom:'4px' },
  scoreBarFill: { height:'100%', borderRadius:'4px', transition:'width .8s' },
  compCard:     { background:'#0A0E18', border:'1px solid', borderRadius:'8px', padding:'12px', flex:1 },
  inputArea:    { padding:'20px 40px', borderTop:'1px solid #1E293B', display:'flex', gap:'10px', alignItems:'center' },
  input:        { flex:1, padding:'14px 20px', background:'#10192B', border:'1px solid #1E293B', borderRadius:'12px', color:'#E2E8F0', fontSize:'14px', outline:'none' },
  compareBtn:   { background:'#1E293B', color:'#F59E0B', border:'1px solid #F59E0B', borderRadius:'12px', padding:'14px 16px', cursor:'pointer', fontSize:'13px', fontWeight:'600', whiteSpace:'nowrap' },
  sendBtn:      { background:'#1E40AF', color:'#fff', border:'none', borderRadius:'12px', width:'50px', height:'50px', cursor:'pointer', fontSize:'18px', flexShrink:0 },
};
