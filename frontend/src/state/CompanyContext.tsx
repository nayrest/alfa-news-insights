import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import type { Company, Role } from '../api/types';

interface AppState {
  companies: Company[];
  current: Company | null;
  select: (id: string) => void;
  roles: Role[];
  role: string;
  setRole: (key: string) => void;
  error: string | null;
}

const Ctx = createContext<AppState>({
  companies: [],
  current: null,
  select: () => {},
  roles: [],
  role: 'ceo',
  setRole: () => {},
  error: null,
});

const COMPANY_KEY = 'alfa-insights:company';
const ROLE_KEY = 'alfa-insights:role';

function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function store(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // приватный режим — просто не запоминаем выбор
  }
}

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(() => readStored(COMPANY_KEY));
  const [roles, setRoles] = useState<Role[]>([]);
  const [role, setRoleState] = useState<string>(() => readStored(ROLE_KEY) ?? 'ceo');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.companies().then(setCompanies).catch((e: Error) => setError(`Не удалось загрузить компании: ${e.message}`));
    api.roles().then(setRoles).catch(() => setRoles([]));
  }, []);

  const select = (id: string) => {
    setCurrentId(id);
    store(COMPANY_KEY, id);
  };
  const setRole = (key: string) => {
    setRoleState(key);
    store(ROLE_KEY, key);
  };

  const current = companies.find((c) => c.id === currentId) ?? companies[0] ?? null;
  return (
    <Ctx.Provider value={{ companies, current, select, roles, role, setRole, error }}>{children}</Ctx.Provider>
  );
}

export const useCompany = () => useContext(Ctx);
