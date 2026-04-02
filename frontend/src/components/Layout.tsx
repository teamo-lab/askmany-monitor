import type { ReactNode } from 'react';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <h1 style={{ fontSize: '1.5em', marginBottom: '24px' }}>
        违禁词监控看板
      </h1>
      {children}
    </div>
  );
}
