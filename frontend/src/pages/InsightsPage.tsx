import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { FeedItem, Insight, InsightKind } from '../api/types';
import { AgentProgress } from '../components/AgentProgress';
import { CompanyProfile } from '../components/CompanyProfile';
import { InsightDetail } from '../components/InsightDetail';
import { KindBadge, RelevanceMeter } from '../components/KindBadge';
import { useCompany } from '../state/CompanyContext';
import { formatShortDate } from '../utils/format';

const FILTERS: { key: 'all' | InsightKind; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'risk', label: 'Риски' },
  { key: 'opportunity', label: 'Возможности' },
  { key: 'neutral', label: 'К сведению' },
];

export function InsightsPage() {
  const { current, roles, role, setRole, error: appError } = useCompany();
  const { id } = useParams();
  const navigate = useNavigate();
  const [feed, setFeed] = useState<FeedItem[] | null>(null);
  const [feedError, setFeedError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | InsightKind>('all');
  const [detail, setDetail] = useState<Insight | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!current) return;
    setFeed(null);
    setFeedError(null);
    api.feed(current.id, role).then(setFeed).catch((e: Error) => setFeedError(e.message));
  }, [current, role]);

  // При смене компании или заходе на /insights открываем самое релевантное событие.
  useEffect(() => {
    if (!feed || feed.length === 0) return;
    if (!id || !feed.some((f) => f.id === id)) navigate(`/insights/${feed[0].id}`, { replace: true });
  }, [feed, id, navigate]);

  const selected = feed?.find((f) => f.id === id) ?? null;

  useEffect(() => {
    if (!current || !selected) return;
    let cancelled = false;
    setDetail(null);
    setDetailError(null);
    api
      .insight(current.id, selected.id, role)
      .then((ins) => {
        if (cancelled) return;
        setDetail(ins);
        // Разбор построен — теперь в ленте известен тип влияния.
        if (ins.status !== 'error') {
          setFeed((f) => f?.map((it) => (it.id === selected.id ? { ...it, kind: ins.kind, lead: ins.lead || it.lead, insight_id: ins.id } : it)) ?? f);
        }
      })
      .catch((e: Error) => !cancelled && setDetailError(e.message));
    return () => {
      cancelled = true;
    };
    // Зависим от selected.id, а не от объекта: обновление kind в ленте не должно перезапрашивать разбор.
  }, [current, selected?.id, role, attempt]);

  if (appError) return <div className="error">{appError}</div>;
  if (!current) return <div className="skeleton skeleton--detail" />;
  const visible = feed?.filter((f) => filter === 'all' || f.kind === filter) ?? [];
  const roleInfo = roles.find((r) => r.key === role);

  return (
    <div className="insights-page">
      <div className="page-head">
        <div>
          <h1>Новостные инсайты</h1>
          <p className="muted">События, отобранные и интерпретированные для вашей компании с учётом аналитики Альфа-Банка</p>
        </div>
        <div className="page-head__tools">
          {roles.length > 0 && (
            <label className="role-select" title={roleInfo?.description}>
              <span>Ваша роль</span>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                {roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
              </select>
            </label>
          )}
        </div>
      </div>

      <CompanyProfile company={current} />

      {feedError && <div className="error">Не удалось загрузить ленту: {feedError}</div>}

      <div className="insights-layout">
        <aside className="feed">
          <div className="feed__filters">
            {FILTERS.map((f) => (
              <button key={f.key} className={`chip-btn${filter === f.key ? ' chip-btn--active' : ''}`} onClick={() => setFilter(f.key)}>
                {f.label}
                {feed && <span className="chip-btn__count">{f.key === 'all' ? feed.length : feed.filter((x) => x.kind === f.key).length}</span>}
              </button>
            ))}
          </div>
          {!feed && !feedError && [0, 1, 2, 3].map((i) => <div key={i} className="skeleton skeleton--card" />)}
          {feed && feed.length === 0 && (
            <p className="muted feed__empty">За последние 30 дней не нашлось событий, связанных с компанией. Новости собираются автоматически каждые полчаса.</p>
          )}
          {feed && feed.length > 0 && visible.length === 0 && <p className="muted feed__empty">Нет событий в этой категории</p>}
          {visible.map((it) => (
            <Link key={it.id} to={`/insights/${it.id}`} className={`feed-item${it.id === id ? ' feed-item--active' : ''} feed-item--${it.kind ?? 'new'}`}>
              <div className="feed-item__meta">
                <KindBadge kind={it.kind} />
                <span>{it.category}</span>
                <span className="feed-item__date">{formatShortDate(it.published_at)}</span>
              </div>
              <div className="feed-item__title">{it.title}</div>
              <div className="feed-item__lead">{it.lead}</div>
              {it.why_selected.length > 0 && (
                <div className="feed-item__why" title={it.why_selected.join('\n')}>
                  Почему в ленте: {it.why_selected[0]}
                  {it.why_selected.length > 1 && ` и ещё ${it.why_selected.length - 1}`}
                </div>
              )}
              <RelevanceMeter value={it.relevance} hint="Релевантность относительно других событий ленты" />
            </Link>
          ))}
        </aside>

        <section className="detail-wrap">
          {detail && <InsightDetail key={detail.id} insight={detail} onRetry={() => setAttempt((a) => a + 1)} />}
          {!detail && detailError && (
            <div className="detail detail--error">
              <h2>Не удалось построить разбор</h2>
              <p className="muted">{detailError}</p>
              <button className="btn btn--outline" onClick={() => setAttempt((a) => a + 1)}>Попробовать ещё раз</button>
            </div>
          )}
          {!detail && !detailError && selected && <AgentProgress item={selected} />}
          {!detail && !detailError && !selected && feed && feed.length > 0 && <div className="skeleton skeleton--detail" />}
        </section>
      </div>
    </div>
  );
}
