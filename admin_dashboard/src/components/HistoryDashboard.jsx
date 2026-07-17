import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, DatePicker, Modal, Pagination, Space, Spin, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { fmtDT } from '../utils/format';

const API = '/api';
const { Text } = Typography;

export default function HistoryDashboard({ t }) {
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [rev, setRev] = useState(0);
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [photoUrl, setPhotoUrl] = useState(null);

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

  const columns = [
    { title: t('plate'), dataIndex: 'plate_number', key: 'plate' },
    { title: t('card'), dataIndex: 'card_uid', key: 'card', render: (v) => v || '-' },
    { title: t('start'), dataIndex: 'start_time', key: 'start', render: (v) => fmtDT(v) },
    { title: t('end'), dataIndex: 'end_time', key: 'end', render: (v) => fmtDT(v) },
    { title: t('dur_h'), dataIndex: 'duration_hours', key: 'duration' },
    { title: t('fare'), dataIndex: 'total_fare', key: 'fare', render: (v) => `Rp ${v.toLocaleString('id-ID')}` },
    {
      title: t('payment'),
      dataIndex: 'forced_billing',
      key: 'payment',
      render: (forced) => <Tag color={forced ? 'warning' : 'success'}>{forced ? 'Forced' : 'Normal'}</Tag>,
    },
    {
      title: 'Foto',
      key: 'photo',
      render: (_, log) => (
        <Button size="small" disabled={!log.snapshot_url} onClick={() => setPhotoUrl(log.snapshot_url)}>
          Lihat
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Modal
        title="Foto Plat"
        open={!!photoUrl}
        onCancel={() => setPhotoUrl(null)}
        footer={null}
      >
        {photoUrl && <img src={`${API}${photoUrl}`} alt="Captured plate" style={{ width: '100%', borderRadius: 8 }} />}
      </Modal>

      <Card>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <Space>
            <Text type="secondary">Date:</Text>
            <DatePicker
              value={date ? dayjs(date) : null}
              onChange={(_, dateString) => { setDate(dateString); setPage(1); }}
              allowClear
              onClear={() => { setDate(''); setPage(1); }}
            />
          </Space>
          <Text type="secondary">
            {t('total_records')}: <Text strong>{total}</Text> | {t('total_revenue')}: <Text strong style={{ color: '#52c41a' }}>Rp {rev.toLocaleString('id-ID')}</Text>
          </Text>
        </div>
      </Card>

      <Card>
        {loading ? (
          <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />
        ) : (
          <Table
            rowKey="id"
            columns={columns}
            dataSource={logs}
            pagination={false}
            locale={{ emptyText: 'No logs' }}
          />
        )}
      </Card>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Pagination
            current={page}
            total={total}
            pageSize={20}
            onChange={setPage}
            showSizeChanger={false}
          />
        </div>
      )}
    </Space>
  );
}
