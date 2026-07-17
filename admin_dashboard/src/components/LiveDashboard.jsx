import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Col, Row, Spin, Table, Tag, Typography, message } from 'antd';

const API = '/api';
const { Text } = Typography;

export default function LiveDashboard({ t }) {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [streamKey1, setStreamKey1] = useState(0);
  const [streamKey2, setStreamKey2] = useState(0);
  const [activeSlot, setActiveSlot] = useState(0);

  const fetchAll = useCallback(async () => {
    try {
      const [sRes, aRes] = await Promise.all([fetch(`${API}/parking/stats`), fetch(`${API}/parking/active`)]);
      const s = await sRes.json(), a = await aRes.json();
      if (s.success) setStats(s.stats);
      if (a.success) setSessions(a.data);
      setLoading(false);
    } catch {
      message.error('Failed to fetch data');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  const getSessionForSlot = (slot) => sessions.find((s) => s.parking_space_id === `SPACE-0${slot}`);

  const columns = [
    { title: t('space'), key: 'space', render: (_, s) => s.space_label || s.parking_space_id },
    { title: t('plate'), dataIndex: 'plate_number', key: 'plate' },
    { title: t('card'), dataIndex: 'card_uid', key: 'card', render: (v) => v || '-' },
    { title: t('duration'), dataIndex: 'duration_minutes', key: 'duration', render: (v) => `${v} min` },
    { title: t('fare'), dataIndex: 'current_fare', key: 'fare', render: (v) => v ? `Rp ${v.toLocaleString('id-ID')}` : '-' },
    {
      title: t('status'),
      dataIndex: 'status',
      key: 'status',
      render: (s) => <Tag color={s === 'ACTIVE' ? 'success' : s === 'WAITING' ? 'warning' : 'default'}>{s}</Tag>,
    },
  ];

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />;

  const renderSlotCamera = (slot, streamKey, setStreamKey) => {
    const active = activeSlot === slot;
    const session = getSessionForSlot(slot);
    return (
      <div style={{ textAlign: 'center' }}>
        <Text strong>Slot {slot}</Text>
        {active ? (
          <img
            src={`${API}/stream/${slot}?t=${streamKey}`}
            alt={`Camera Slot ${slot}`}
            style={{ width: '100%', borderRadius: 12, border: '2px solid #e8e8e8', marginTop: 8, minHeight: 240, background: '#f5f5f5' }}
            onError={() => { setActiveSlot(0); setTimeout(() => setStreamKey(Date.now()), 3000); }}
          />
        ) : (
          <div
            onClick={() => setActiveSlot(slot)}
            style={{ width: '100%', borderRadius: 12, border: '2px dashed #d9d9d9', marginTop: 8, minHeight: 240, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
          >
            <Text type="secondary">Klik untuk lihat stream</Text>
          </div>
        )}
        {session?.snapshot_url && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>Plat terdeteksi</Text>
            <img
              src={`${API}${session.snapshot_url}`}
              alt={`Captured plate slot ${slot}`}
              style={{ width: '100%', borderRadius: 8, border: '1px solid #d9d9d9' }}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {stats && (
        <Row gutter={[16, 16]}>
          <Col xs={12} lg={6}>
            <Card style={{ background: 'linear-gradient(135deg, #52c41a, #389e0d)', color: '#fff' }}>
              <div style={{ opacity: 0.85 }}>{t('active_sessions')}</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{stats.active_sessions}</div>
            </Card>
          </Col>
          <Col xs={12} lg={6}>
            <Card style={{ background: 'linear-gradient(135deg, #faad14, #d48806)', color: '#fff' }}>
              <div style={{ opacity: 0.85 }}>{t('waiting_reg')}</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{stats.waiting_registration}</div>
            </Card>
          </Col>
          <Col xs={12} lg={6}>
            <Card style={{ background: 'linear-gradient(135deg, #1890ff, #096dd9)', color: '#fff' }}>
              <div style={{ opacity: 0.85 }}>{t('today_revenue')}</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>Rp {(stats.today_revenue || 0).toLocaleString('id-ID')}</div>
            </Card>
          </Col>
          <Col xs={12} lg={6}>
            <Card style={{ background: 'linear-gradient(135deg, #722ed1, #531dab)', color: '#fff' }}>
              <div style={{ opacity: 0.85 }}>{t('today_sessions')}</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{stats.today_sessions}</div>
            </Card>
          </Col>
        </Row>
      )}

      <Card
        title={`${t('tab_live')} Parking`}
        extra={<Button type="primary" onClick={fetchAll}>{t('refresh')}</Button>}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={sessions}
          pagination={false}
          locale={{ emptyText: t('no_active') }}
        />
      </Card>

      <Card title="Live Camera Stream">
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>{renderSlotCamera(1, streamKey1, setStreamKey1)}</Col>
          <Col xs={24} md={12}>{renderSlotCamera(2, streamKey2, setStreamKey2)}</Col>
        </Row>
      </Card>
    </div>
  );
}
