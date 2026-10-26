// Приведение ответов бэкенда к модели интерфейса (api/types.ts).
import type { ApiFeedItem, ApiInsight, ApiProfile, ApiTrace } from './backend';
import type { Company, FeedItem, Insight, InsightKind, Source, Statement, TraceStep } from './types';
import { companyDisplay } from '../config/companies';

const PRODUCT_LABELS: Record<keyof ApiProfile['products'], string> = {
  rko: 'РКО',
  loans: 'Кредиты',
  guarantees: 'Банковские гарантии',
  leasing: 'Лизинг',
  deposits: 'Депозиты',
  salary_project: 'Зарплатный проект',
  factoring: 'Факторинг',
};

const CLIENT_TYPES: Record<string, string> = {
  CLIENT: 'Действующий клиент',
  CLOSE_CLIENT: 'Закрывающийся клиент',
  PROSPECT: 'Потенциальный клиент',
};

export const TOPIC_LABELS: Record<string, string> = {
  key_rate: 'Ключевая ставка',
  inflation: 'Инфляция',
  fx: 'Валюта',
  debt_market: 'Долговой рынок',
  sanctions: 'Санкции',
  trade_policy: 'ВЭД и пошлины',
  tax_regulation: 'Налоги и регулирование',
  commodities: 'Сырьё',
  labor: 'Рынок труда',
  logistics: 'Логистика',
  consumer_demand: 'Потребление',
  gdp_macro: 'Макроэкономика',
};

// Ключи отраслей совпадают с backend/app/companies/profile.py::SECTOR_NAMES_RU
const SECTOR_RU: Record<string, string> = {
  agriculture: 'сельское хозяйство',
  oil_gas: 'нефть и газ',
  mining_metals: 'добыча и металлургия',
  food: 'пищевая промышленность',
  chemicals: 'химия',
  manufacturing: 'обрабатывающая промышленность',
  auto: 'автомобильная отрасль',
  energy: 'энергетика',
  construction: 'строительство',
  retail_trade: 'торговля',
  transport_logistics: 'транспорт и логистика',
  it_telecom: 'ИТ и связь',
  finance: 'финансы',
  real_estate: 'недвижимость',
  other: 'прочее',
  // контрагента нет среди компаний датасета — отрасль определить не по чему
  unknown: 'нет в данных кейса',
};

/** 'ЮЖНАЯ КОРЕЯ' -> 'Южная Корея', аббревиатуры (ОАЭ, США) не трогаем. */
function countryLabel(raw: string): string {
  const s = raw.trim();
  if (s.length <= 3) return s;
  return s.toLowerCase().replace(/(^|[\s-])\S/g, (m) => m.toUpperCase());
}

function countriesOf(ft: ApiProfile['foreign_trade']): string[] {
  const list = ft.countries ?? (ft.country ? ft.country.split(/[,;]/) : []);
  return [...new Set(list.map(countryLabel).filter(Boolean))];
}

const toCounterparties = (list: ApiProfile['counterparties']['suppliers']) =>
  list.map((c) => ({ ...c, sector: SECTOR_RU[c.sector] ?? c.sector }));

export function toCompany(p: ApiProfile, index: number): Company {
  const display = companyDisplay(p.id, p.sector_ru, index);
  return {
    id: p.id,
    ...display,
    okved_code: p.okved_code ?? '',
    okved_name: p.okved_name ?? '',
    sector: p.sector_ru,
    revenue: p.revenue,
    client_type_label: (p.client_type && CLIENT_TYPES[p.client_type]) || p.client_type || 'нет данных',
    products: (Object.keys(PRODUCT_LABELS) as (keyof ApiProfile['products'])[])
      .filter((k) => p.products[k])
      .map((k) => PRODUCT_LABELS[k]),
    has_loans: p.products.loans,
    fts_flag: p.foreign_trade.has_fts,
    fts_countries: countriesOf(p.foreign_trade),
    negative_mark: p.negative_mark,
    eco_stage: p.eco_stage,
    age: p.company_age,
    workers: p.workers,
    ownership: p.ownership,
    city: p.city,
    region: p.region,
    group: { id: p.group.group_id, size: p.group.group_size },
    market: {
      share: p.market.share_in_okved_dataset,
      rank: p.market.rank_in_okved_dataset,
      total: p.market.companies_in_okved_dataset,
    },
    counterparties: {
      suppliers: toCounterparties(p.counterparties.suppliers),
      buyers: toCounterparties(p.counterparties.buyers),
    },
    linked_companies: p.linked_companies_via_persons ?? [],
  };
}

function categoryOf(tags: ApiFeedItem['tags']): string {
  const topic = tags?.topics?.find((t) => TOPIC_LABELS[t]);
  return topic ? TOPIC_LABELS[topic] : 'Новости';
}

export function toFeedItem(n: ApiFeedItem, companyId: string, maxScore: number): FeedItem {
  return {
    id: String(n.id),
    company_id: companyId,
    title: n.title,
    // У части RSS-новостей нет описания — тогда показываем, почему событие отобрано
    lead: n.insight_headline || n.summary.slice(0, 220) || n.why_selected[0] || '',
    kind: null,
    category: categoryOf(n.tags),
    relevance: maxScore > 0 ? n.score / maxScore : 0,
    published_at: n.published_at,
    publisher: n.source,
    why_selected: n.why_selected,
    insight_id: n.insight_id != null ? String(n.insight_id) : null,
  };
}

export function kindOf(risks: number, opportunities: number): InsightKind {
  if (!risks && !opportunities) return 'neutral';
  return risks >= opportunities ? 'risk' : 'opportunity';
}

function sourcesOf(payload: ApiInsight['insight'], news?: FeedItem): Source[] {
  const entries = Object.entries(payload.sources ?? {});
  const order = (id: string) => (id.startsWith('N') ? 0 : 1) * 1000 + Number(id.slice(1));
  return entries
    .sort(([a], [b]) => order(a) - order(b))
    .map(([id, s]) =>
      id.startsWith('A')
        ? { id, title: s.doc ?? id, type: 'bank_analytics' as const, publisher: 'Аналитика Альфа-Банка', excerpt: s.text }
        : {
            id,
            title: s.title ?? id,
            type: 'news' as const,
            publisher: s.source ?? '',
            url: s.url,
            date: id === 'N1' ? news?.published_at : null,
          },
    );
}

function splitFeature(desc: string) {
  const i = desc.indexOf(': ');
  return i > 0 ? { label: desc.slice(0, i), value: desc.slice(i + 2) } : { label: 'Признак', value: desc };
}

export function toInsight(api: ApiInsight, trace: ApiTrace | null, news?: FeedItem): Insight {
  const p = api.insight;
  const features = p.features ?? {};
  const risks = p.risks ?? [];
  const opps = p.opportunities ?? [];
  const facts: Statement[] = (p.facts ?? []).map((f) => ({ text: f.text, source_ids: [f.source] }));
  return {
    id: String(api.id),
    news_id: String(api.news_id),
    company_id: api.company_id,
    status: api.status,
    error: p.error,
    title: news?.title ?? p.sources?.N1?.title ?? 'Событие',
    lead: p.headline ?? '',
    what_happened: p.what_happened ?? '',
    kind: kindOf(risks.length, opps.length),
    category: news?.category ?? 'Новости',
    relevance: p.relevance ?? news?.relevance ?? 0,
    horizon: p.horizon ?? '',
    published_at: news?.published_at ?? null,
    url: p.sources?.N1?.url,
    facts,
    bank_view: (p.bank_view ?? []).map((b) => ({ text: b.text, source_ids: [b.source] })),
    ai: {
      why_important: p.why_important ?? '',
      inferences: (p.ai_inference ?? []).map((i) => ({ text: i.text, source_ids: i.based_on ?? [] })),
      consequences: [
        ...risks.map((r) => ({ kind: 'risk' as const, text: r.text })),
        ...opps.map((o) => ({ kind: 'opportunity' as const, text: o.text })),
      ],
      actions: (p.actions ?? []).map((a) => a.text),
      questions: p.questions_to_check ?? [],
      product_hint: p.bank_product_hint ?? null,
    },
    company_factors: (p.client_features_used ?? []).map((key) => splitFeature(features[key] ?? key)),
    feature_labels: features,
    sources: sourcesOf(p, news),
    trace: trace ? toTrace(trace) : [],
  };
}

const STEP_LABELS: Record<string, [string, string]> = {
  rule_match: ['Отбор правилами', 'score_news'],
  plan: ['Планирование', 'LLM: план'],
  'tool:search_alfa_analytics': ['Поиск в аналитике банка', 'search_alfa_analytics'],
  'tool:search_related_news': ['Поиск связанных новостей', 'search_related_news'],
  'tool:get_counterparties': ['Контрагенты компании', 'get_counterparties'],
  'self_check:rules': ['Самопроверка правилами', 'validate'],
  'self_check:critic': ['Проверка критиком', 'LLM: критик'],
  adapt: ['Адаптация: дозапрос данных', 'search_alfa_analytics'],
  error: ['Ошибка', '—'],
};

const list = (v: unknown) => (Array.isArray(v) ? v.map(String).join('; ') : '');

function stepDetail(s: ApiTrace['trace'][number]): string {
  switch (s.step) {
    case 'rule_match':
      return `Совпавшие признаки: ${list(s.matched) || 'нет'}`;
    case 'plan': {
      const out = (s.output ?? {}) as Record<string, unknown>;
      return list(out.steps) || JSON.stringify(out).slice(0, 300);
    }
    case 'tool:search_alfa_analytics':
      return `Запросы: ${list(s.queries)}. Найдено: ${list(s.found) || 'ничего'}`;
    case 'tool:search_related_news':
      return `Запрос: ${String(s.query)}. Найдено: ${list(s.found) || 'ничего'}`;
    case 'self_check:rules':
      return `Версия ${Number(s.revision) + 1}: ${list(s.issues) || 'замечаний нет'}`;
    case 'self_check:critic': {
      const out = (s.output ?? {}) as Record<string, unknown>;
      return out.ok === false ? `Замечания: ${list(out.issues)}` : 'Вывод принят';
    }
    case 'adapt':
      return `Фрагменты аналитики после дозапроса: ${list(s.extra_analytics)}`;
    case 'error':
      return String(s.message ?? '');
    default: {
      const { step: _step, t: _t, ...rest } = s;
      return JSON.stringify(rest).slice(0, 300);
    }
  }
}

export function toTrace(trace: ApiTrace): TraceStep[] {
  return trace.trace.map((s) => {
    const [step, tool] = STEP_LABELS[s.step] ?? [s.step, s.step];
    return { step, tool, detail: stepDetail(s) };
  });
}
