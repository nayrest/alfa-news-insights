import { useState } from 'react';
import type { Insight, Statement } from '../api/types';
import { formatDate } from '../utils/format';
import { AskPanel } from './AskPanel';
import { IconBank, IconChat, IconDoc, IconLink, IconRoute, IconSpark } from './Icons';
import { KindBadge, RelevanceMeter } from './KindBadge';
import { TraceDrawer } from './TraceDrawer';

/** Ссылки утверждения: [n] — источник, Ф1/Б1 — факт или позиция банка, остальное — признак клиента. */
function Refs({ ids, insight }: { ids: string[]; insight: Insight }) {
  return (
    <>
      {ids.map((id) => {
        const n = insight.sources.findIndex((s) => s.id === id) + 1;
        if (n > 0) {
          return <a key={id} href={`#src-${id}`} className="src-ref" title={insight.sources[n - 1].title}>[{n}]</a>;
        }
        const m = /^([FB])(\d+)$/.exec(id);
        if (m) return <span key={id} className={`ref-chip ref-chip--${m[1] === 'F' ? 'fact' : 'bank'}`}>{m[1] === 'F' ? 'факт' : 'банк'} {m[2]}</span>;
        const label = insight.feature_labels[id];
        return label ? <span key={id} className="ref-chip ref-chip--feature" title={id}>{label}</span> : null;
      })}
    </>
  );
}

function StatementList({ items, insight, numbered }: { items: Statement[]; insight: Insight; numbered?: string }) {
  return (
    <ul className="statements">
      {items.map((s, i) => (
        <li key={i}>
          {numbered && <span className="statements__id">{numbered} {i + 1}</span>}
          {s.text} <Refs ids={s.source_ids} insight={insight} />
        </li>
      ))}
    </ul>
  );
}

export function InsightDetail({ insight, onRetry }: { insight: Insight; onRetry: () => void }) {
  const [traceOpen, setTraceOpen] = useState(false);
  const [askOpen, setAskOpen] = useState(false);

  if (insight.status === 'error') {
    return (
      <article className="detail detail--error">
        <h1 className="detail__title">{insight.title}</h1>
        <h2>Агент не смог построить разбор</h2>
        <p className="muted">{insight.error || 'Ошибка обращения к языковой модели.'}</p>
        <div className="detail__actions">
          <button className="btn btn--outline" onClick={() => setTraceOpen(true)}><IconRoute /> Что произошло</button>
          <button className="btn btn--outline" onClick={onRetry}>Попробовать ещё раз</button>
        </div>
        {traceOpen && <TraceDrawer insight={insight} onClose={() => setTraceOpen(false)} />}
      </article>
    );
  }

  return (
    <article className="detail">
      <header className="detail__head">
        <div className="detail__meta">
          <KindBadge kind={insight.kind} />
          <span className="tag">{insight.category}</span>
          {insight.horizon && <span className="tag">Горизонт: {insight.horizon}</span>}
          {insight.published_at && <span className="muted">{formatDate(insight.published_at)}</span>}
          <RelevanceMeter value={insight.relevance} hint="Важность события для компании (оценка агента)" />
        </div>
        <h1 className="detail__title">{insight.title}</h1>
        {insight.lead && <p className="detail__lead">{insight.lead}</p>}
        {insight.status === 'partial' && (
          <p className="detail__warning">Самопроверка нашла замечания, которые агент не успел исправить. Сверьтесь с источниками.</p>
        )}
        <div className="detail__actions">
          <button className="btn btn--outline" onClick={() => setTraceOpen(true)}><IconRoute /> Как получен вывод</button>
          <button className="btn btn--primary" onClick={() => setAskOpen(true)}><IconChat /> Задать вопрос</button>
          {insight.url && (
            <a className="btn btn--outline" href={insight.url} target="_blank" rel="noreferrer"><IconLink /> Первоисточник</a>
          )}
        </div>
      </header>

      <section className="block block--facts">
        <h2 className="block__title"><IconDoc /> Что произошло <span className="block__hint">подтверждённые факты</span></h2>
        {insight.what_happened && insight.facts.length === 0 && <p>{insight.what_happened}</p>}
        <StatementList items={insight.facts} insight={insight} numbered="факт" />
      </section>

      <section className="block block--bank">
        <h2 className="block__title"><IconBank /> Позиция Альфа-Банка <span className="block__hint">аналитика ЦМИ</span></h2>
        {insight.bank_view.length > 0
          ? <StatementList items={insight.bank_view} insight={insight} numbered="банк" />
          : <p className="muted">В аналитических материалах банка не нашлось позиции по этому событию.</p>}
      </section>

      <section className="block block--ai">
        <h2 className="block__title"><IconSpark /> Вывод AI для вашей компании <span className="block__hint">сформировано моделью на основе фактов, аналитики и признаков компании</span></h2>
        {insight.ai.why_important && (
          <>
            <h3>Почему это важно</h3>
            <p>{insight.ai.why_important}</p>
          </>
        )}
        {insight.ai.inferences.length > 0 && (
          <>
            <h3>Выводы</h3>
            <StatementList items={insight.ai.inferences} insight={insight} />
          </>
        )}
        {insight.ai.consequences.length > 0 && (
          <>
            <h3>Возможные последствия</h3>
            <ul className="consequences">
              {insight.ai.consequences.map((c, i) => (
                <li key={i} className={`consequence consequence--${c.kind}`}>
                  <KindBadge kind={c.kind} /> <span>{c.text}</span>
                </li>
              ))}
            </ul>
          </>
        )}
        {insight.ai.actions.length > 0 && (
          <>
            <h3>Что можно сделать</h3>
            <ol className="actions-list">
              {insight.ai.actions.map((a, i) => <li key={i}>{a}</li>)}
            </ol>
          </>
        )}
        {insight.ai.questions.length > 0 && (
          <>
            <h3>Что стоит проверить</h3>
            <ul className="actions-list">
              {insight.ai.questions.map((q, i) => <li key={i}>{q}</li>)}
            </ul>
          </>
        )}
      </section>

      {insight.ai.product_hint && (
        <section className="product-hint">
          <span className="product-hint__label">Альфа-Банк может помочь</span>
          <p>{insight.ai.product_hint}</p>
        </section>
      )}

      {insight.company_factors.length > 0 && (
        <section className="block block--plain">
          <h2 className="block__title">Признаки компании, учтённые в выводе</h2>
          <div className="factors">
            {insight.company_factors.map((f, i) => (
              <div key={i} className="factor"><span>{f.label}</span><b>{f.value}</b></div>
            ))}
          </div>
        </section>
      )}

      <section className="block block--plain">
        <h2 className="block__title">Источники</h2>
        <ol className="sources">
          {insight.sources.map((s) => (
            <li key={s.id} id={`src-${s.id}`}>
              <span className={`source-type source-type--${s.type}`}>{s.type === 'bank_analytics' ? 'Аналитика банка' : 'Новость'}</span>
              <span className="sources__title">{s.title}</span>
              <span className="muted">{s.publisher}{s.date ? ` · ${formatDate(s.date)}` : ''}</span>
              {s.url && <a href={s.url} target="_blank" rel="noreferrer" className="sources__link"><IconLink width={16} height={16} /> Открыть</a>}
              {s.excerpt && <blockquote className="sources__excerpt">{s.excerpt.slice(0, 400)}{s.excerpt.length > 400 ? '…' : ''}</blockquote>}
            </li>
          ))}
        </ol>
      </section>

      {traceOpen && <TraceDrawer insight={insight} onClose={() => setTraceOpen(false)} />}
      {askOpen && <AskPanel insight={insight} onClose={() => setAskOpen(false)} />}
    </article>
  );
}
