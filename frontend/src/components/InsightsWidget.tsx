import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { FeedItem } from '../api/types';
import { useCompany } from '../state/CompanyContext';
import { formatShortDate } from '../utils/format';
import { IconChevron, IconSpark } from './Icons';
import { KindBadge } from './KindBadge';

export function InsightsWidget() {
  const { current, role } = useCompany();
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!current) return;
    setItems(null);
    setError(false);
    api
      .feed(current.id, role)
      .then((feed) => setItems(feed.slice(0, 3)))
      .catch(() => setError(true));
  }, [current, role]);

  return (
    <section className="card insights-widget">
      <header className="card__header">
        <Link to="/insights" className="card__title">
          <span className="insights-widget__icon"><IconSpark width={18} height={18} /></span>
          Инсайты для вашего бизнеса
          <span className="badge-new">НОВОЕ</span>
        </Link>
        <Link to="/insights" aria-label="Открыть все инсайты"><IconChevron /></Link>
      </header>

      {!items && !error && <div className="insights-widget__list">{[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton--row" />)}</div>}
      {error && <p className="muted insights-widget__empty">Сервис инсайтов временно недоступен</p>}
      {items && items.length === 0 && <p className="muted insights-widget__empty">Свежих событий для компании пока нет</p>}

      {items && items.length > 0 && (
        <ul className="insights-widget__list">
          {items.map((it) => (
            <li key={it.id}>
              <Link to={`/insights/${it.id}`} className="insights-widget__item">
                <div className="insights-widget__meta">
                  <KindBadge kind={it.kind} />
                  <span>{it.category}</span>
                  {it.published_at && <><span>·</span><span>{formatShortDate(it.published_at)}</span></>}
                </div>
                <div className="insights-widget__title">{it.title}</div>
                <div className="insights-widget__lead">{it.lead}</div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Link to="/insights" className="btn btn--secondary btn--block">Все инсайты</Link>
    </section>
  );
}
