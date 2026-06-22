/* STOPBAY PWA - App Logic */

// ========================================
// i18n — Bilingual (ID / EN) with toggle
// ========================================
const i18n = {
  id: {
    app_name: 'STOPBAY', app_subtitle: 'Parkir Cerdas',
    lookup_title: 'Cek Status Parkir', lookup_desc: 'Masukkan UID kartu KTP/KTM Anda',
    card_uid_label: 'UID Kartu', check_btn: 'Cek Status',
    current_fare_label: 'Biaya Parkir', hours: 'Jam', minutes: 'Menit',
    total_min: 'Total', balance: 'Saldo', session_details: 'Detail Sesi',
    plate_label: 'Plat', space_label: 'Slot', card_label: 'Kartu',
    user_label: 'User', status_label: 'Status', entry_label: 'Masuk',
    refresh_btn: 'Refresh', loading: 'Memuat data...',
    error_conn: 'Gagal terhubung ke server', error_not_found: 'Tidak ada sesi aktif',
    toast_ok: 'Berhasil!', toast_refresh: 'Data diperbarui',
  },
  en: {
    app_name: 'STOPBAY', app_subtitle: 'Smart Parking',
    lookup_title: 'Check Parking Status', lookup_desc: 'Enter your KTP/KTM card UID',
    card_uid_label: 'Card UID', check_btn: 'Check Status',
    current_fare_label: 'Parking Fee', hours: 'Hours', minutes: 'Minutes',
    total_min: 'Total', balance: 'Balance', session_details: 'Session Details',
    plate_label: 'Plate', space_label: 'Slot', card_label: 'Card',
    user_label: 'User', status_label: 'Status', entry_label: 'Entry',
    refresh_btn: 'Refresh', loading: 'Loading data...',
    error_conn: 'Failed to connect to server', error_not_found: 'No active session',
    toast_ok: 'Success!', toast_refresh: 'Data updated',
  }
};

let lang = localStorage.getItem('stopbay_lang') || 'id';
function t(key) { return i18n[lang][key] || key; }
function applyLang() {
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
}

document.getElementById('langToggle').addEventListener('click', () => {
  lang = lang === 'id' ? 'en' : 'id';
  localStorage.setItem('stopbay_lang', lang);
  applyLang();
});

// ========================================
// API Config
// ========================================
const API_BASE = 'http://192.168.1.100:8000';
let refreshTimer = null;
let lastCardUID = '';

// ========================================
// Toast Notification
// ========================================
function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = `fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl text-white text-sm font-medium shadow-xl z-50 transition-all duration-300 ${type === 'error' ? 'bg-red-500' : 'bg-brand-600'}`;
  toast.classList.add('toast-show');
  setTimeout(() => toast.classList.remove('toast-show'), 2500);
}

// ========================================
// View Switcher
// ========================================
function showView(view) {
  document.getElementById('lookupView').classList.add('hidden');
  document.getElementById('parkingView').classList.add('hidden');
  document.getElementById('loadingView').classList.add('hidden');
  if (view) document.getElementById(view).classList.remove('hidden');
}

// ========================================
// Format Helpers
// ========================================
function fmtRupiah(n) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
function fmtDateTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return `${d.getDate()}/${d.getMonth()+1}/${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

// ========================================
// API Fetch
// ========================================
async function fetchStatus(cardUID) {
  try {
    const res = await fetch(`${API_BASE}/api/parking/status/${cardUID}`);
    const data = await res.json();
    return data;
  } catch (e) {
    return { success: false, message: t('error_conn') };
  }
}

async function fetchUser(cardUID) {
  try {
    const res = await fetch(`${API_BASE}/api/users/${cardUID}`);
    const data = await res.json();
    return data;
  } catch { return { success: false }; }
}

// ========================================
// Lookup
// ========================================
document.getElementById('lookupBtn').addEventListener('click', async () => {
  const uid = document.getElementById('uidInput').value.trim().toUpperCase();
  if (!uid) return;

  showView('loadingView');
  document.getElementById('lookupError').classList.add('hidden');

  const [statusData, userData] = await Promise.all([fetchStatus(uid), fetchUser(uid)]);

  if (statusData.success && statusData.data) {
    lastCardUID = uid;
    updateParkingView(statusData.data, userData.success ? userData.data : null);
    showView('parkingView');
    startAutoRefresh();
  } else {
    showView('lookupView');
    document.getElementById('lookupError').textContent = statusData.message || t('error_not_found');
    document.getElementById('lookupError').classList.remove('hidden');
  }
});

// Also trigger on Enter key
document.getElementById('uidInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('lookupBtn').click();
});

// ========================================
// Update Parking View
// ========================================
function updateParkingView(data, user) {
  const h = Math.floor(data.duration_minutes / 60);
  const m = Math.floor(data.duration_minutes % 60);
  const fare = data.current_fare || 0;

  document.getElementById('fareAmount').textContent = 'Rp ' + fmtRupiah(fare);
  document.getElementById('fareRate').textContent = 'Rp ' + fmtRupiah(data.fare_per_hour || 2000) + ' / ' + (lang === 'id' ? 'jam' : 'hour');
  document.getElementById('durHours').textContent = h;
  document.getElementById('durMinutes').textContent = m;
  document.getElementById('durTotalMin').textContent = data.duration_minutes || 0;
  document.getElementById('balanceAmount').textContent = user ? 'Rp ' + fmtRupiah(user.balance) : '-';
  document.getElementById('detPlate').textContent = data.plate_number;
  document.getElementById('detSpace').textContent = data.space_label || data.parking_space_id;
  document.getElementById('detCard').textContent = data.card_uid || '-';
  document.getElementById('detUser').textContent = data.user_name || '-';
  document.getElementById('detStatus').textContent = data.status;
  document.getElementById('detEntry').textContent = fmtDateTime(data.entry_time);
}

// ========================================
// Auto Refresh
// ========================================
function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(async () => {
    const data = await fetchStatus(lastCardUID);
    const user = await fetchUser(lastCardUID);
    if (data.success && data.data) {
      updateParkingView(data.data, user.success ? user.data : null);
    } else {
      stopAutoRefresh();
      showView('lookupView');
      document.getElementById('lookupError').textContent = t('error_not_found');
      document.getElementById('lookupError').classList.remove('hidden');
      showToast(t('error_not_found'), 'error');
    }
  }, 5000);
}

function stopAutoRefresh() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}

// Manual refresh button
document.getElementById('refreshBtn').addEventListener('click', async () => {
  if (!lastCardUID) return;
  document.getElementById('refreshBtn').classList.add('animate-spin');
  const data = await fetchStatus(lastCardUID);
  const user = await fetchUser(lastCardUID);
  if (data.success && data.data) {
    updateParkingView(data.data, user.success ? user.data : null);
    showToast(t('toast_refresh'));
  }
  document.getElementById('refreshBtn').classList.remove('animate-spin');
});

// ========================================
// Init
// ========================================
applyLang();
showView('lookupView');
