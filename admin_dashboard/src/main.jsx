import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import App from './App';
import 'antd/dist/reset.css';
import './index.css';

// ponytail: single theme object, inline; no separate theme config file until needed
const theme = {
  token: {
    colorPrimary: '#7CB9E8',
    colorInfo: '#7CB9E8',
    borderRadius: 8,
  },
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider theme={theme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
