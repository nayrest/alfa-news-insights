import { useEffect } from 'react';
import type { Insight } from '../api/types';
import { IconClose } from './Icons';

export function Drawer({ title, subtitle, onClose, children }: { title: string; subtitle?: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <header className="drawer__head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Закрыть"><IconClose /></button>
        </header>
        <div className="drawer__body">{children}</div>
      </aside>
    </div>
  );
}

export function TraceDrawer({ insight, onClose }: { insight: Insight; onClose: () => void }) {
  return (
    <Drawer title="Как получен вывод" subtitle="Шаги агента, инструменты и промежуточные результаты" onClose={onClose}>
      <ol className="trace">
        {insight.trace.map((t, i) => (
          <li key={i} className="trace__step">
            <span className="trace__num">{i + 1}</span>
            <div>
              <div className="trace__name">{t.step} <code>{t.tool}</code></div>
              <div className="trace__detail">{t.detail}</div>
            </div>
          </li>
        ))}
      </ol>
      <h3 className="drawer__subtitle">Что повлияло на вывод</h3>
      <div className="factors">
        {insight.company_factors.map((f) => (
          <div key={f.label} className="factor"><span>{f.label}</span><b>{f.value}</b></div>
        ))}
      </div>
    </Drawer>
  );
}
