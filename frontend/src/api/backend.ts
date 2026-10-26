// Форматы ответов FastAPI-бэкенда (backend/app/main.py, backend/app/schemas.py).

export interface ApiCompanyListItem {
  id: string;
  sector: string | null;
  okved: string;
  region: string | null;
  revenue: number | null;
}

export interface ApiProfile {
  id: string;
  okved_code: string | null;
  okved_name: string | null;
  sector: string;
  sector_ru: string;
  region: string | null;
  city: string | null;
  revenue: number | null;
  market: {
    share_in_okved_dataset: number | null;
    rank_in_okved_dataset: number | null;
    companies_in_okved_dataset: number;
  };
  products: Record<'rko' | 'loans' | 'leasing' | 'deposits' | 'guarantees' | 'salary_project' | 'factoring', boolean>;
  // countries — список стран ВЭД (появился в бэкенде позже, country оставлен для совместимости)
  foreign_trade: { has_fts: boolean; country: string | null; countries?: string[] };
  group: { group_id: string | null; group_size: number };
  workers: string | null;
  client_type: string | null;
  company_age: string | null;
  eco_stage: string | null;
  negative_mark: boolean;
  ownership: string | null;
  linked_companies_via_persons?: string[];
  counterparties: {
    suppliers: { id: string; share: number; sector: string }[];
    buyers: { id: string; share: number; sector: string }[];
  };
}

export interface ApiFeedItem {
  id: number;
  title: string;
  summary: string;
  url: string;
  source: string;
  published_at: string | null;
  tags: { topics?: string[]; sectors?: string[]; countries?: string[] } | null;
  score: number;
  why_selected: string[];
  insight_id: number | null;
  insight_headline: string | null;
}

interface ApiRef {
  text: string;
  based_on?: string[];
}

export interface ApiInsightPayload {
  headline?: string;
  what_happened?: string;
  why_important?: string;
  facts?: { id: string; text: string; source: string; confirmed?: boolean }[];
  bank_view?: { id: string; text: string; source: string }[];
  ai_inference?: { id: string; text: string; based_on: string[] }[];
  client_features_used?: string[];
  risks?: ApiRef[];
  opportunities?: ApiRef[];
  actions?: ApiRef[];
  questions_to_check?: string[];
  bank_product_hint?: string | null;
  relevance?: number;
  horizon?: string;
  sources?: Record<string, { title?: string; url?: string; source?: string; doc?: string; text?: string }>;
  features?: Record<string, string>;
  error?: string;
}

export interface ApiInsight {
  id: number;
  company_id: string;
  news_id: number;
  role: string;
  status: 'ok' | 'partial' | 'error';
  created_at: string;
  insight: ApiInsightPayload;
}

export interface ApiTrace {
  insight_id: number;
  status: string;
  trace: ({ step: string; t?: number } & Record<string, unknown>)[];
}

export interface ApiAskAnswer {
  question: string;
  answer?: string;
  based_on?: string[];
  source_links?: string[];
}
