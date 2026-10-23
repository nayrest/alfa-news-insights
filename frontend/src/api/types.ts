// Модель данных интерфейса. Ответы бэкенда приводятся к ней в api/adapter.ts,
// поэтому компоненты не зависят от формата API.

export interface Counterparty {
  id: string;
  share: number;
  sector: string;
}

export interface Company {
  id: string;
  name: string;
  short: string;
  color: string;
  okved_code: string;
  okved_name: string;
  sector: string;
  revenue: number | null;
  client_type_label: string;
  products: string[];
  has_loans: boolean;
  fts_flag: boolean;
  fts_countries: string[];
  negative_mark: boolean;
  eco_stage: string | null;
  age: string | null;
  workers: string | null;
  ownership: string | null;
  city: string | null;
  region: string | null;
  group: { id: string | null; size: number; revenue?: number; top_okved?: string[] };
  market?: { share: number | null; rank: number | null; total: number };
  counterparties?: { suppliers: Counterparty[]; buyers: Counterparty[] };
}

export interface Role {
  key: string;
  label: string;
  description: string;
}

export type InsightKind = 'risk' | 'opportunity' | 'neutral';

export interface Source {
  id: string;
  title: string;
  type: 'news' | 'bank_analytics';
  publisher: string;
  date?: string | null;
  url?: string | null;
  excerpt?: string;
}

/** Утверждение со ссылками на источники или признаки клиента. */
export interface Statement {
  text: string;
  source_ids: string[];
}

export interface Consequence {
  kind: Exclude<InsightKind, 'neutral'>;
  text: string;
}

/** Признак компании, который повлиял на вывод. */
export interface CompanyFactor {
  label: string;
  value: string;
}

/** Шаг агента — для «Как получен вывод». */
export interface TraceStep {
  step: string;
  tool: string;
  detail: string;
}

/** Событие в ленте компании. id — идентификатор новости. */
export interface FeedItem {
  id: string;
  company_id: string;
  title: string;
  lead: string;
  /** null — разбор агентом ещё не построен, тип влияния неизвестен */
  kind: InsightKind | null;
  category: string;
  relevance: number; // 0..1
  published_at: string | null;
  publisher: string;
  why_selected: string[];
  insight_id: string | null;
}

export interface Insight {
  id: string;
  news_id: string;
  company_id: string;
  status: 'ok' | 'partial' | 'error';
  error?: string;
  title: string;
  lead: string;
  what_happened: string;
  kind: InsightKind;
  category: string;
  relevance: number; // 0..1
  horizon: string;
  published_at: string | null;
  url?: string | null;
  facts: Statement[];
  bank_view: Statement[];
  ai: {
    why_important: string;
    inferences: Statement[];
    consequences: Consequence[];
    actions: string[];
    questions: string[];
    product_hint: string | null;
  };
  company_factors: CompanyFactor[];
  /** Расшифровка ключей признаков клиента, на которые ссылаются выводы AI */
  feature_labels: Record<string, string>;
  sources: Source[];
  trace: TraceStep[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  source_ids?: string[];
}
