import React, { useState } from 'react';
import { Layout, Tabs, Button, Typography } from 'antd';
import LiveDashboard from './components/LiveDashboard';
import HistoryDashboard from './components/HistoryDashboard';
import UsersDashboard from './components/UsersDashboard';
import HardwareDashboard from './components/HardwareDashboard';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

// ponytail: inline i18n map preserved from original; no external i18n lib needed for two langs
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
    start: 'Start', end: 'End', dur_h: 'Durasi', payment: 'Payment',
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

  const items = [
    { key: 'live', label: t('tab_live'), children: <LiveDashboard t={t} /> },
    { key: 'history', label: t('tab_history'), children: <HistoryDashboard t={t} /> },
    { key: 'users', label: t('tab_users'), children: <UsersDashboard t={t} /> },
    { key: 'hardware', label: t('tab_hardware'), children: <HardwareDashboard t={t} /> },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: 'linear-gradient(90deg, #5A9BD5, #7CB9E8)', color: '#fff', padding: '16px 24px', height: 'auto', lineHeight: 'normal' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* ponytail: logo placed in public/logo.png; update filename if different */}
            <img src="/logo.png" alt="STOPBAY logo" style={{ height: 48, width: 'auto', objectFit: 'contain', borderRadius: 4, background: '#fff' }} />
            <div>
              <Title level={3} style={{ color: '#fff', margin: 0, lineHeight: 1.2 }}>{t('title')}</Title>
              <Text style={{ color: 'rgba(255,255,255,0.85)' }}>{t('subtitle')}</Text>
            </div>
          </div>
          <Button onClick={toggleLang}>
            {t('language')}: {lang === 'id' ? 'ID' : 'EN'}
          </Button>
        </div>
      </Header>
      <Content style={{ maxWidth: 1200, margin: '0 auto', padding: 24, width: '100%' }}>
        <Tabs activeKey={tab} onChange={setTab} items={items} />
      </Content>
    </Layout>
  );
}
