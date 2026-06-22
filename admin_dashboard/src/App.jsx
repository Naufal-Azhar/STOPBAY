import React, { useState, useEffect, useCallback, useRef } from 'react';

const API = '/api';

// i18n texts
const TXT = {
  id: {
    title: 'STOPBAY Admin', subtitle: 'Ticketless Smart Parking System',
    tab_live: 'Live', tab_history: 'Riwayat', tab_users: 'Pengguna', tab_hardware: 'Hardware',
    active_sessions: 'Sesi Aktif', waiting_reg: 'Menunggu Registrasi', today_revenue: 'Pendapatan Hari Ini', today_sessions: 'Sesi Hari Ini',
    space: 'Slot', plate: 'Plat', card: 'Kartu', duration: 'Durasi', fare: 'Biaya', status: 'Status',
    no_active: 'Tidak ada sesi parkir aktif', refresh: 'Refresh',
    card_uid: 'UID Kartu', name: 'Nama', nik: 'NIK', email: 'Email', balance: 'Saldo', created: 'Dibuat',
    topup: 'Top Up', topup_amt: 'Jumlah', cancel: 'Batal', confirm: 'Konfirmasi',
    device_id: 'ID Device', device_type: 'Tipe', location: 'Lokasi', online: 'Online', offline: 'Offline', last_hb: 'Heartbeat Terakhir',
    page: 'Halaman', of: 'dari', total_records: 'Total', total_revenue: 'Pendapatan',
    start: 'Mulai', end: 'Selesai', dur_h: 'Durasi', payment: 'Pembayaran',
    language: 'Bahasa',
  },
  en: {
    title: 'STOPBAY Admin', subtitle: 'Ticketless Smart Parking System',
    tab_live: 'Live', tab_history: 'History', tab_users: 'Users', tab_hardware: 'Hardware',
    active_sessions: 'Active Sessions', waiting_reg: 'Waiting Registration', today_revenue: 'Today Revenue', today_sessions: 'Today Sessions',
    space: 'Slot', plate: 'Plate', card: 'Card', duration: 'Duration', fare: 'Fare', status: 'Status',
    no_active: 'No active parking sessions', refresh: 'Refresh',
    card_uid: 'Card UID', name: 'Name', nik: 'NIK', email: 'Email', balance: 'Balance', created: 'Created',
    topup: 'Top Up', topup_amt: 'Amount', cancel: 'Cancel', confirm: 'Confirm',
    device_id: 'Device ID', device_type: 'Type', location: 'Location', online: 'Online', offline: 'Offline', last_hb: 'Last Heartbeat',
    page: 'Page', of: 'of', total_records: 'Total Records', total_revenue: 'Total Revenue',
    start: 'Start', end: 'End', dur_h: 'Duration', payment: 'Payment',
    language: 'Language',
  }
};

export default function App() {
  const [tab, setTab] = useState('live');
  const [lang, setLang] = useState(localStorage.getItem('stopbay_admin_lang') || 'id');
  const t = (k) => TXT[lang][k] || k;

  const toggleLang = () => {
    const next = lang === 'id' ? 'en' : 'id';
    setLang(next);
    localStorage.setItem('stopbay_admin_lang', next);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-emerald-700 to-emerald-500 text-white px-6 py-5 shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
            <p className="text-emerald-100 text-sm mt-1">{t('subtitle')}</p>
          </div>
          <button onClick={toggleLang}
            className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:scale-105">
            {t('language')}: {lang === 'id' ? '🇮🇩 ID' : '🇬🇧 EN'}
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex overflow-x-auto">
          {['live','history','users','hardware'].map((tb) => (
            <button key={tb} onClick={() => setTab(tb)}
              className={`px-6 py-3.5 font-medium text-sm transition-all duration-200 border-b-2 whitespace-nowrap ${
                tab === tb ? 'border-emerald-600 text-emerald-600 bg-emerald-50/50' : 'border-transparent text-gray-500 hover:text-emerald-600 hover:border-emerald-300'
              }`}>
              {t('tab_' + tb)}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <AnimatedDiv key={tab}>
          {tab === 'live' && <LiveDashboard t={t} />}
          {tab === 'history' && <HistoryDashboard t={t} />}
          {tab === 'users' && <UsersDashboard t={t} />}
          {tab === 'hardware' && <HardwareDashboard t={t} />}
        </AnimatedDiv>
      </main>
    </div>
  );
}

// Wrapper for tab transition
function AnimatedDiv({ children, key }) {
  return (
    <div key={key} className="animate-fadeSlide" style={{
      animation: 'fadeSlideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1)'
    }}>
      {children}
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

/* ============================================================
   Live Dashboard
   ============================================================ */
function LiveDashboard({ t }) {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      const [sRes, aRes] = await Promise.all([fetch(`${API}/parking/stats`), fetch(`${API}/parking/active`)]);
      const s = await sRes.json(), a = await aRes.json();
      if (s.success) setStats(s.stats);
      if (a.success) setSessions(a.data);
      setToast(''); setLoading(false);
    } catch { setToast('Failed to fetch data'); setLoading(false); }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  if (loading) return <Spinner />;
  return (
    <div className="space-y-6">
      {toast && <Toast msg={toast} type="error" onClose={() => setToast('')} />}

      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card color="from-emerald-500 to-emerald-600" icon="🅿️" label={t('active_sessions')} value={stats.active_sessions} />
          <Card color="from-amber-500 to-amber-600" icon="⏳" label={t('waiting_reg')} value={stats.waiting_registration} />
          <Card color="from-blue-500 to-blue-600" icon="💰" label={t('today_revenue')} value={`Rp ${(stats.today_revenue||0).toLocaleString('id-ID')}`} />
          <Card color="from-violet-500 to-violet-600" icon="📊" label={t('today_sessions')} value={stats.today_sessions} />
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h2 className="font-semibold text-gray-800">{t('tab_live')} Parking</h2>
          <button onClick={fetchAll} className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-sm transition-all duration-200 active:scale-95">
            {t('refresh')}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {[t('space'), t('plate'), t('card'), t('duration'), t('fare'), t('status')].map((h) => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.length === 0 ? (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-gray-400">{t('no_active')}</td></tr>
              ) : sessions.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors duration-150">
                  <td className="px-5 py-3.5 text-sm font-medium">{s.space_label || s.parking_space_id}</td>
                  <td className="px-5 py-3.5 text-sm">{s.plate_number}</td>
                  <td className="px-5 py-3.5 text-sm font-mono text-gray-500">{s.card_uid || '-'}</td>
                  <td className="px-5 py-3.5 text-sm">{s.duration_minutes} min</td>
                  <td className="px-5 py-3.5 text-sm">{s.current_fare ? `Rp ${s.current_fare.toLocaleString('id-ID')}` : '-'}</td>
                  <td className="px-5 py-3.5 text-sm"><Badge s={s.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   History Dashboard
   ============================================================ */
function HistoryDashboard({ t }) {
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [rev, setRev] = useState(0);
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      let url = `${API}/parking/logs?page=${page}&per_page=20`;
      if (date) url += `&date=${date}`;
      const res = await fetch(url), d = await res.json();
      if (d.success) { setLogs(d.data); setTotalPages(d.total_pages); setTotal(d.total); setRev(d.total_revenue); }
    } catch {} finally { setLoading(false); }
  }, [page, date]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const headers = [t('plate'), t('card'), t('start'), t('end'), t('dur_h'), t('fare'), t('payment')];

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border p-4 flex flex-wrap gap-3 items-center justify-between">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-500">Date:</label>
          <input type="date" value={date} onChange={(e) => { setDate(e.target.value); setPage(1); }}
            className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-emerald-500 outline-none" />
          {date && <button onClick={() => { setDate(''); setPage(1); }} className="text-xs text-red-500 hover:underline">Clear</button>}
        </div>
        <div className="text-sm text-gray-500">{t('total_records')}: <b>{total}</b> | {t('total_revenue')}: <b className="text-emerald-600">Rp {rev.toLocaleString('id-ID')}</b></div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>{headers.map((h) => (<th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? <tr><td colSpan={7}><Spinner /></td></tr> : logs.length === 0
                ? <tr><td colSpan={7} className="px-5 py-10 text-center text-gray-400">No logs</td></tr>
                : logs.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50 transition-colors duration-150">
                    <td className="px-5 py-3 text-sm font-medium">{l.plate_number}</td>
                    <td className="px-5 py-3 text-sm font-mono text-gray-500">{l.card_uid || '-'}</td>
                    <td className="px-5 py-3 text-xs text-gray-500">{fmtDT(l.start_time)}</td>
                    <td className="px-5 py-3 text-xs text-gray-500">{fmtDT(l.end_time)}</td>
                    <td className="px-5 py-3 text-sm">{l.duration_hours}h</td>
                    <td className="px-5 py-3 text-sm font-semibold text-emerald-600">Rp {l.total_fare.toLocaleString('id-ID')}</td>
                    <td className="px-5 py-3 text-xs">{l.forced_billing ? <span className="text-amber-600 font-medium">Forced</span> : <span className="text-emerald-600">Normal</span>}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 items-center">
          <button onClick={() => setPage((p) => Math.max(1, p-1))} disabled={page===1} className="px-4 py-2 bg-white border rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-all duration-200 text-sm">{'<'}</button>
          <span className="px-3 text-sm text-gray-500">{t('page')} {page} {t('of')} {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p+1))} disabled={page===totalPages} className="px-4 py-2 bg-white border rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-all duration-200 text-sm">{'>'}</button>
        </div>
      )}
    </div>
  );
}

/* ============================================================
   Users Dashboard
   ============================================================ */
function UsersDashboard({ t }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [topupUid, setTopupUid] = useState(null);
  const [topupAmt, setTopupAmt] = useState(50000);
  const [toast, setToast] = useState('');

  const fetchUsers = useCallback(async () => {
    try {
      const r = await fetch(`${API}/users`), d = await r.json();
      if (d.success) setUsers(d.data);
    } catch { setToast('Failed to fetch'); } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const doTopup = async () => {
    if (!topupUid || topupAmt <= 0) return;
    try {
      const r = await fetch(`${API}/users/${topupUid}/topup`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: topupAmt }),
      });
      const d = await r.json();
      if (d.success) { setToast(`Top-up Rp ${topupAmt.toLocaleString('id-ID')} berhasil!`); setTopupUid(null); fetchUsers(); }
      else setToast('Top-up gagal');
    } catch { setToast('Connection error'); }
  };

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast} onClose={() => setToast('')} />}

      {/* Topup Modal */}
      {topupUid && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4 animate-popIn">
            <h3 className="text-lg font-bold text-gray-800 mb-1">{t('topup')}</h3>
            <p className="text-sm text-gray-500 mb-4">UID: <b className="font-mono">{topupUid}</b></p>
            <input type="number" min="1000" max="10000000" value={topupAmt} onChange={(e) => setTopupAmt(Number(e.target.value))}
              className="w-full border rounded-xl px-4 py-2.5 text-lg text-center focus:ring-2 focus:ring-emerald-500 outline-none mb-4" />
            <div className="flex gap-2">
              <button onClick={() => setTopupUid(null)} className="flex-1 py-2.5 border border-gray-200 rounded-xl hover:bg-gray-50 transition-all duration-200 text-sm">{t('cancel')}</button>
              <button onClick={doTopup} className="flex-1 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 font-semibold transition-all duration-200 text-sm active:scale-95">{t('confirm')}</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {[t('card_uid'), t('name'), t('nik'), t('email'), t('balance'), t('created'), ''].map((h) => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.card_uid} className="hover:bg-gray-50 transition-colors duration-150">
                  <td className="px-5 py-3 text-sm font-mono">{u.card_uid}</td>
                  <td className="px-5 py-3 text-sm">{u.full_name}</td>
                  <td className="px-5 py-3 text-xs text-gray-500">{u.nik}</td>
                  <td className="px-5 py-3 text-xs text-gray-500">{u.email}</td>
                  <td className="px-5 py-3 text-sm font-semibold text-emerald-600">Rp {u.balance.toLocaleString('id-ID')}</td>
                  <td className="px-5 py-3 text-xs text-gray-400">{fmtDT(u.created_at)}</td>
                  <td className="px-5 py-3">
                    <button onClick={() => { setTopupUid(u.card_uid); setTopupAmt(50000); }}
                      className="px-3 py-1.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-lg hover:bg-emerald-200 transition-all duration-200 active:scale-95">
                      {t('topup')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Hardware Status Dashboard
   ============================================================ */
function HardwareDashboard({ t }) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHW = useCallback(async () => {
    try {
      const r = await fetch(`${API}/hardware/status`), d = await r.json();
      if (d.success) setDevices(d.data);
    } catch {} finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchHW();
    const iv = setInterval(fetchHW, 10000);
    return () => clearInterval(iv);
  }, [fetchHW]);

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {devices.map((dev) => (
          <div key={dev.device_id}
            className={`rounded-xl p-4 text-center shadow-sm border transition-all duration-300 hover:scale-105 ${
              dev.is_online ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50 animate-pulse'
            }`}>
            <div className={`w-3 h-3 mx-auto rounded-full mb-2 ${dev.is_online ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
            <p className="text-sm font-semibold">{dev.device_id}</p>
            <p className="text-xs text-gray-500">{dev.device_type}</p>
            <p className={`text-xs font-medium mt-1 ${dev.is_online ? 'text-emerald-600' : 'text-red-500'}`}>
              {dev.is_online ? '✅ ' + t('online') : '❌ ' + t('offline')}
            </p>
            <p className="text-xs text-gray-400 mt-1">{fmtDT(dev.last_heartbeat)}</p>
          </div>
        ))}
        {devices.length === 0 && <p className="text-gray-400 col-span-full text-center py-8">No devices tracked</p>}
      </div>
    </div>
  );
}

/* ============================================================
   Shared Components
   ============================================================ */
function Card({ color, icon, label, value }) {
  return (
    <div className={`bg-gradient-to-br ${color} rounded-xl shadow-md p-5 text-white transition-all duration-300 hover:scale-105 hover:shadow-lg`}>
      <div className="flex justify-between items-start">
        <div><p className="text-xs opacity-80">{label}</p><p className="text-2xl font-bold mt-1">{value}</p></div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}

function Badge({ s }) {
  const cls = s === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : s === 'WAITING' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600';
  return <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${cls}`}>{s}</span>;
}

function Toast({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return (
    <div className={`fixed bottom-6 right-6 px-5 py-3 rounded-xl text-white text-sm font-medium shadow-xl z-50 animate-slideIn ${type === 'error' ? 'bg-red-500' : 'bg-emerald-600'}`}>
      {msg}
      <style>{`@keyframes slideIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}`}</style>
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center items-center py-16"><div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin"></div></div>;
}

function fmtDT(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleString('id-ID', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
}
