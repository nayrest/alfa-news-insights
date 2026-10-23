import type { ApiAskAnswer, ApiCompanyListItem, ApiFeedItem, ApiInsight, ApiProfile, ApiTrace } from './backend';
import type { ChatMessage, Company, FeedItem, Insight, Role } from './types';
import { kindOf, toCompany, toFeedItem, toInsight } from './adapter';
import { MAX_COMPANIES, PREFERRED_COMPANY_IDS } from '../config/companies';
import { mockAsk, mockCompanies, mockFeed, mockInsight, mockRoles } from '../mocks';

// VITE_USE_MOCKS=true — демо-данные без бэкенда (для вёрстки и показа без ключа LLM).
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';
// Бэкенд отдаёт роуты без префикса; /api снимает прокси (vite.config.ts, nginx.conf.template).
const API_URL = import.meta.env.VITE_API_URL ?? '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? String(body.detail) : `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

const delay = <T,>(value: T, ms = 250) => new Promise<T>((resolve) => setTimeout(() => resolve(value), ms));

// Лента нужна и списку, и карточке события — кэшируем последнюю на компанию и роль.
const feedCache = new Map<string, FeedItem[]>();

async function loadFeed(companyId: string, role: string): Promise<FeedItem[]> {
  const raw = await request<ApiFeedItem[]>(`/companies/${companyId}/feed?role=${role}&days=30&limit=30`);
  const maxScore = Math.max(0, ...raw.map((n) => n.score));
  const items = raw.map((n) => toFeedItem(n, companyId, maxScore));
  // Тип влияния знаем только у событий, по которым агент уже строил разбор.
  await Promise.all(
    items
      .filter((it) => it.insight_id)
      .map(async (it) => {
        const ins = await request<ApiInsight>(`/insights/${it.insight_id}`).catch(() => null);
        if (ins && ins.status !== 'error') {
          it.kind = kindOf(ins.insight.risks?.length ?? 0, ins.insight.opportunities?.length ?? 0);
        }
      }),
  );
  return items;
}

const inflight = new Map<string, Promise<Insight>>();

async function buildInsight(companyId: string, newsId: string, role: string): Promise<Insight> {
  const news = feedCache.get(`${companyId}:${role}`)?.find((n) => n.id === newsId);
  const created = await request<ApiInsight>(`/companies/${companyId}/insights`, {
    method: 'POST',
    body: JSON.stringify({ news_id: Number(newsId), role }),
  });
  const trace = await request<ApiTrace>(`/insights/${created.id}/trace`).catch(() => null);
  return toInsight(created, trace, news);
}

export const api = {
  async companies(): Promise<Company[]> {
    if (USE_MOCKS) return delay(mockCompanies);
    const list = await request<ApiCompanyListItem[]>('/companies?limit=500');
    const preferred = PREFERRED_COMPANY_IDS.filter((id) => list.some((c) => c.id === id));
    const ids = (preferred.length ? preferred : list.map((c) => c.id)).slice(0, MAX_COMPANIES);
    const profiles = await Promise.all(ids.map((id) => request<ApiProfile>(`/companies/${id}`)));
    return profiles.map(toCompany);
  },

  async roles(): Promise<Role[]> {
    if (USE_MOCKS) return delay(mockRoles);
    const roles = await request<Record<string, string>>('/roles');
    return Object.entries(roles).map(([key, description]) => ({ key, label: description.split(':')[0], description }));
  },

  async feed(companyId: string, role: string): Promise<FeedItem[]> {
    const items = USE_MOCKS ? await delay(mockFeed(companyId)) : await loadFeed(companyId, role);
    feedCache.set(`${companyId}:${role}`, items);
    return items;
  },

  /** Разбор события для компании. Если его ещё нет — бэкенд запускает агента (может занять до минуты). */
  insight(companyId: string, newsId: string, role: string): Promise<Insight> {
    if (USE_MOCKS) return delay(mockInsight(newsId), 600);
    // Один и тот же разбор не запрашиваем параллельно: каждый запуск агента тратит дневной лимит токенов.
    const key = `${companyId}:${newsId}:${role}`;
    const pending = inflight.get(key);
    if (pending) return pending;
    const promise = buildInsight(companyId, newsId, role).finally(() => inflight.delete(key));
    inflight.set(key, promise);
    return promise;
  },

  async ask(insight: Insight, question: string): Promise<ChatMessage> {
    if (USE_MOCKS) return delay(mockAsk(insight.id, question), 900);
    const res = await request<ApiAskAnswer>(`/insights/${insight.id}/ask`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    });
    return { role: 'assistant', text: res.answer ?? 'Модель не дала ответа.', source_ids: res.based_on ?? [] };
  },
};
