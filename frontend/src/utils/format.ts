import type { InsightKind } from '../api/types';

export function formatBillions(rub: number | null | undefined): string {
  if (rub == null) return 'выручка н/д';
  return `${(rub / 1e9).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} млрд ₽`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return 'дата неизвестна';
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export function formatPercent(share: number): string {
  return `${(share * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`;
}

export const KIND_LABEL: Record<InsightKind, string> = {
  risk: 'Риск',
  opportunity: 'Возможность',
  neutral: 'К сведению',
};
