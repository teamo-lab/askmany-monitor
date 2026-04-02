import { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, theme } from 'antd';
import {
  AlertOutlined,
  ApiOutlined,
  DashboardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { TimeRangeProvider } from './context/TimeRangeContext';
import { DrilldownProvider } from './context/DrilldownContext';
import { TimeRangeSelector } from './components/TimeRangeSelector';
import { ForbiddenWordPage } from './pages/ForbiddenWordPage';
import { ComingSoonPage } from './pages/ComingSoonPage';

const { Header, Sider, Content } = Layout;

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();

  const menuItems = [
    { key: '/', icon: <AlertOutlined />, label: '违禁词监控' },
    { key: '/api-monitor', icon: <ApiOutlined />, label: 'API 监控' },
    { key: '/model-usage', icon: <RobotOutlined />, label: '模型调用' },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="light"
        style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}>
        <div style={{
          height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}>
          <DashboardOutlined style={{ fontSize: 20, color: token.colorPrimary }} />
          {!collapsed && <span style={{ marginLeft: 8, fontWeight: 600 }}>Monitor</span>}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: token.colorBgContainer,
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          height: 48,
          lineHeight: '48px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {collapsed
              ? <MenuUnfoldOutlined onClick={() => setCollapsed(false)} style={{ fontSize: 16, cursor: 'pointer' }} />
              : <MenuFoldOutlined onClick={() => setCollapsed(true)} style={{ fontSize: 16, cursor: 'pointer' }} />}
            <span style={{ fontSize: 16, fontWeight: 600 }}>AskMany Monitor</span>
          </div>
          <TimeRangeSelector />
        </Header>
        <Content style={{ margin: 16, padding: 16, background: token.colorBgLayout }}>
          <Routes>
            <Route path="/" element={<ForbiddenWordPage />} />
            <Route path="/api-monitor" element={<ComingSoonPage title="API 监控" />} />
            <Route path="/model-usage" element={<ComingSoonPage title="模型调用" />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <TimeRangeProvider>
        <DrilldownProvider>
          <AppLayout />
        </DrilldownProvider>
      </TimeRangeProvider>
    </BrowserRouter>
  );
}

export default App;
