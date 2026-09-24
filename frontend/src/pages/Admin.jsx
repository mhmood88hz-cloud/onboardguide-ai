import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Admin() {
  const [adminToken, setAdminToken] = useState(localStorage.getItem('admin_token') || '');
  const [tokenInput,  setTokenInput]  = useState('');
  const [orgs,        setOrgs]        = useState([]);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState('');
  const [activateFor, setActivateFor] = useState(null); // org id currently being activated
  const [untilDate,   setUntilDate]   = useState('');
  const [billingName,    setBillingName]    = useState('');
  const [billingAddress, setBillingAddress] = useState('');
  const [invoicesFor,    setInvoicesFor]    = useState(null); // org id, dessen Rechnungen gerade offen sind
  const [invoices,       setInvoices]       = useState([]);
  const [invoicesLoading,setInvoicesLoading]= useState(false);

  const call = (method, path, data) =>
    axios({
      method, data,
      url: `${API_URL}${path}`,
      headers: { 'x-admin-token': adminToken },
    });

  const loadOrgs = (token) => {
    setLoading(true);
    setError('');
    axios.get(`${API_URL}/api/platform/organizations`, {
      headers: { 'x-admin-token': token || adminToken },
    })
      .then(res => setOrgs(res.data))
      .catch(() => {
        setError('Admin-Token ungültig oder Server nicht erreichbar.');
        localStorage.removeItem('admin_token');
        setAdminToken('');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (adminToken) loadOrgs(adminToken); }, []); // eslint-disable-line

  const handleUnlock = () => {
    if (!tokenInput.trim()) return;
    localStorage.setItem('admin_token', tokenInput.trim());
    setAdminToken(tokenInput.trim());
    loadOrgs(tokenInput.trim());
  };

  const handleDeactivate = async (org) => {
    if (!window.confirm(`Firma '${org.name}' wirklich sofort sperren?`)) return;
    try {
      await call('post', `/api/platform/organizations/${org.id}/deactivate`);
      loadOrgs();
    } catch {
      alert('Fehler beim Sperren.');
    }
  };

  const handleActivate = async (org) => {
    try {
      await call('post', `/api/platform/organizations/${org.id}/activate`, {
        plan: 'active',
        active_until: untilDate ? new Date(untilDate).toISOString() : null,
        billing_contact_name: billingName || null,
        billing_address: billingAddress || null,
      });
      setActivateFor(null);
      setUntilDate('');
      setBillingName('');
      setBillingAddress('');
      loadOrgs();
    } catch {
      alert('Fehler beim Freischalten.');
    }
  };

  const toggleInvoices = async (org) => {
    if (invoicesFor === org.id) { setInvoicesFor(null); return; }
    setInvoicesFor(org.id);
    setInvoicesLoading(true);
    try {
      const res = await call('get', `/api/platform/organizations/${org.id}/invoices`);
      setInvoices(res.data);
    } catch {
      setInvoices([]);
    } finally {
      setInvoicesLoading(false);
    }
  };

  const downloadInvoice = async (org, invoice) => {
    try {
      const res = await axios({
        method: 'get',
        url: `${API_URL}/api/platform/organizations/${org.id}/invoices/${invoice.id}/pdf`,
        headers: { 'x-admin-token': adminToken },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${invoice.invoice_number}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Rechnung konnte nicht geladen werden.');
    }
  };

  const statusOf = (org) => {
    if (!org.is_active) return { text: 'Gesperrt', color: '#e0665a' };
    if (org.active_until && new Date(org.active_until) < new Date()) {
      return { text: 'Abgelaufen', color: '#d9a83e' };
    }
    if (org.active_until) return { text: `Aktiv bis ${new Date(org.active_until).toLocaleDateString('de-DE')}`, color: '#4caf6d' };
    return { text: 'Aktiv (unbefristet)', color: '#4caf6d' };
  };

  if (!adminToken) {
    return (
      <div className="gx-aurora" style={s.page}>
        <div className="gx-card" style={s.gate}>
          <div style={s.logoRow}>
            <span style={s.logoIcon}>🛡️</span>
            <span style={s.logoText}>Owner-Bereich</span>
          </div>
          <p style={s.tagline}>Firmenzugänge freischalten oder sperren</p>
          <label style={s.label}>Admin-Token</label>
          <input
            className="gx-input"
            style={s.input}
            type="password"
            placeholder="ADMIN_TOKEN aus der .env"
            value={tokenInput}
            onChange={e => setTokenInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleUnlock()}
          />
          {error && <p style={s.error}>{error}</p>}
          <button className="gx-btn" style={s.button} onClick={handleUnlock}>Entsperren</button>
        </div>
      </div>
    );
  }

  return (
    <div className="gx-aurora" style={s.dashPage}>
      <div style={s.main}>
        <div style={s.header}>
          <div>
            <h1 style={s.title}>Owner-Bereich</h1>
            <p style={s.subtitle}>Alle Firmen über alle Mandanten hinweg — Abrechnung ohne Stripe, manuell nach Absprache.</p>
          </div>
          <button
            className="gx-btn"
            style={s.logoutBtn}
            onClick={() => { localStorage.removeItem('admin_token'); setAdminToken(''); setOrgs([]); }}
          >
            Sperren
          </button>
        </div>

        <div className="gx-card" style={s.card}>
          <div style={s.tableHeader}>
            <span style={{flex: 2}}>FIRMA</span>
            <span style={{flex: 1}}>PLAN</span>
            <span style={{flex: 2}}>STATUS</span>
            <span style={{flex: 2}}>AKTION</span>
          </div>

          {loading ? (
            <p style={{color: '#8fa1ae', padding: '16px 0'}}>Laden...</p>
          ) : orgs.length === 0 ? (
            <p style={{color: '#8fa1ae', padding: '16px 0'}}>Keine Firmen vorhanden.</p>
          ) : orgs.map(org => {
            const status = statusOf(org);
            return (
              <div key={org.id}>
                <div className="gx-row" style={s.row}>
                  <div style={{flex: 2}}>
                    <div style={{color: '#eef3f7', fontWeight: '600', fontSize: '14px'}}>{org.name}</div>
                    <div style={{color: '#748998', fontSize: '12px'}}>{org.slug} · seit {new Date(org.created_at).toLocaleDateString('de-DE')}</div>
                  </div>
                  <div style={{flex: 1, color: '#8fa1ae', fontSize: '13px'}}>{org.plan}</div>
                  <div style={{flex: 2, color: status.color, fontSize: '13px', fontWeight: '600'}}>{status.text}</div>
                  <div style={{flex: 2, display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center'}}>
                    {org.is_active ? (
                      <button className="gx-btn" style={s.dangerBtn} onClick={() => handleDeactivate(org)}>Sperren</button>
                    ) : activateFor !== org.id && (
                      <button className="gx-btn" style={s.successBtn} onClick={() => { setActivateFor(org.id); setBillingName(org.billing_contact_name || ''); setBillingAddress(org.billing_address || ''); }}>Freischalten</button>
                    )}
                    <button className="gx-btn" style={s.invoiceBtn} onClick={() => toggleInvoices(org)}>
                      {invoicesFor === org.id ? 'Rechnungen ▲' : 'Rechnungen ▼'}
                    </button>
                  </div>
                </div>

                {activateFor === org.id && (
                  <div style={s.activatePanel}>
                    <label style={s.label}>Freigeschaltet bis (leer = unbefristet)</label>
                    <input className="gx-input" style={s.dateInput} type="date"
                           value={untilDate} onChange={e => setUntilDate(e.target.value)} />
                    <label style={s.label}>Rechnungsempfänger (Kontaktperson)</label>
                    <input className="gx-input" style={s.panelInput} placeholder="z.B. Max Mustermann"
                           value={billingName} onChange={e => setBillingName(e.target.value)} />
                    <label style={s.label}>Rechnungsadresse</label>
                    <textarea className="gx-input" style={{...s.panelInput, height: '60px', resize: 'vertical'}}
                              placeholder={"Straße Hausnummer\nPLZ Ort"}
                              value={billingAddress} onChange={e => setBillingAddress(e.target.value)} />
                    <div style={{display: 'flex', gap: '8px', marginTop: '4px'}}>
                      <button className="gx-btn" style={s.successBtn} onClick={() => handleActivate(org)}>Bestätigen &amp; Rechnung erstellen</button>
                      <button className="gx-btn" style={s.cancelBtn} onClick={() => { setActivateFor(null); setUntilDate(''); setBillingName(''); setBillingAddress(''); }}>Abbrechen</button>
                    </div>
                  </div>
                )}

                {invoicesFor === org.id && (
                  <div style={s.activatePanel}>
                    {invoicesLoading ? (
                      <p style={{color: '#8fa1ae', fontSize: '13px', margin: 0}}>Laden...</p>
                    ) : invoices.length === 0 ? (
                      <p style={{color: '#8fa1ae', fontSize: '13px', margin: 0}}>Noch keine Rechnungen.</p>
                    ) : invoices.map(inv => (
                      <div key={inv.id} style={s.invoiceRow}>
                        <span style={{color: '#eef3f7', fontSize: '13px', fontWeight: '600'}}>{inv.invoice_number}</span>
                        <span style={{color: '#8fa1ae', fontSize: '12px'}}>
                          {inv.employee_count} × {inv.unit_price_eur.toFixed(2)} € = {inv.total_eur.toFixed(2)} €
                        </span>
                        <span style={{color: '#748998', fontSize: '12px'}}>
                          {new Date(inv.created_at).toLocaleDateString('de-DE')}
                        </span>
                        <button className="gx-btn" style={s.downloadBtn} onClick={() => downloadInvoice(org, inv)}>PDF ↓</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const s = {
  page:      { minHeight: '100vh', background: '#0d141c', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Segoe UI, sans-serif' },
  gate:      { borderRadius: '20px', padding: '48px', width: '420px', boxSizing: 'border-box' },
  logoRow:   { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' },
  logoIcon:  { fontSize: '32px' },
  logoText:  { color: '#eef3f7', fontSize: '24px', fontWeight: '700' },
  tagline:   { color: '#e3a24d', fontSize: '14px', marginBottom: '32px', marginTop: 0 },
  label:     { color: '#8fa1ae', fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '6px' },
  input:     { width: '100%', padding: '13px 16px', background: '#0d141c', border: '1px solid #edb268', borderRadius: '10px', color: '#eef3f7', fontSize: '14px', outline: 'none', boxSizing: 'border-box', marginBottom: '20px' },
  error:     { color: '#e0665a', fontSize: '13px', marginBottom: '12px', textAlign: 'center' },
  button:    { width: '100%', padding: '14px', background: '#e3a24d', color: '#1a1206', border: 'none', borderRadius: '10px', fontSize: '16px', fontWeight: '700', cursor: 'pointer' },

  dashPage:  { minHeight: '100vh', background: '#0d141c', fontFamily: 'Segoe UI, sans-serif' },
  main:      { maxWidth: '1000px', margin: '0 auto', padding: '40px' },
  header:    { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px', gap: '16px', flexWrap: 'wrap' },
  title:     { color: '#eef3f7', fontSize: '28px', fontWeight: '700', margin: '0 0 6px' },
  subtitle:  { color: '#8fa1ae', margin: 0, fontSize: '14px', maxWidth: '520px' },
  logoutBtn: { background: '#26343f', color: '#8fa1ae', border: 'none', padding: '10px 18px', borderRadius: '8px', cursor: 'pointer', fontWeight: '600', height: 'fit-content' },
  card:      { borderRadius: '16px', padding: '8px 24px', marginBottom: '24px' },
  tableHeader: { display: 'flex', padding: '16px 0', borderBottom: '1px solid #26343f', color: '#748998', fontSize: '11px', fontWeight: '700', letterSpacing: '1px' },
  row:       { display: 'flex', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid #26343f', gap: '8px' },
  dangerBtn: { background: '#240b08', color: '#e0665a', border: 'none', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: '600' },
  successBtn:{ background: '#0d1f14', color: '#4caf6d', border: 'none', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: '600' },
  cancelBtn: { background: '#1a2732', color: '#8fa1ae', border: 'none', padding: '8px 12px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px' },
  dateInput: { padding: '8px 10px', background: '#0d141c', border: '1px solid #26343f', borderRadius: '8px', color: '#eef3f7', fontSize: '13px', outline: 'none', marginBottom: '14px' },
  invoiceBtn:  { background: '#1a2732', color: '#8fa1ae', border: 'none', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px' },
  activatePanel: { background: '#0d141c', border: '1px solid #26343f', borderRadius: '12px', padding: '16px 20px', marginBottom: '16px', display: 'flex', flexDirection: 'column' },
  panelInput:  { width: '100%', padding: '10px 14px', background: '#141e29', border: '1px solid #26343f', borderRadius: '8px', color: '#eef3f7', fontSize: '13px', outline: 'none', boxSizing: 'border-box', marginBottom: '14px' },
  invoiceRow:  { display: 'flex', alignItems: 'center', gap: '16px', padding: '10px 0', borderBottom: '1px solid #1a2732' },
  downloadBtn: { marginLeft: 'auto', background: '#1a2732', color: '#edb268', border: 'none', padding: '6px 12px', borderRadius: '8px', cursor: 'pointer', fontSize: '12px', fontWeight: '600' },
};
