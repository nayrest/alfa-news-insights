import type { InsightKind } from '../api/types';
import { KIND_LABEL } from '../utils/format';

/** kind = null — агент ещё не разбирал событие, тип влияния неизвестен. */
export function KindBadge({ kind }: { kind: InsightKind | null }) {
  if (!kind) return <span className="kind-badge kind-badge--new" title="Разбор агентом ещё не построен">Новое</span>;
  return <span className={`kind-badge kind-badge--${kind}`}>{KIND_LABEL[kind]}</span>;
}

export function RelevanceMeter({ value, hint = 'Релевантность для компании' }: { value: number; hint?: string }) {
  const pct = Math.round(value * 100);
  return (
    <span className="relevance" title={`${hint}: ${pct}%`}>
      <span className="relevance__bar"><span style={{ width: `${pct}%` }} /></span>
      <span className="relevance__value">{pct}%</span>
    </span>
  );
}
