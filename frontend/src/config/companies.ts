// Какие компании показывать в переключателе и как их называть.
// В датасете компании обезличены, поэтому названия явно условные — «Клиент А · …»,
// чтобы их нельзя было спутать с реальными фирмами.

const DISPLAY: Record<string, { name: string; short: string; color: string }> = {
  U_34911: { name: 'Клиент А · зерновой трейдер', short: 'А', color: '#F5C451' },
  U_9250: { name: 'Клиент Б · инфраструктурное строительство', short: 'Б', color: '#7AC4FF' },
  U_200890: { name: 'Клиент В · металлотрейдер', short: 'В', color: '#B9C2CC' },
  U_102920: { name: 'Клиент Г · импортёр продуктов', short: 'Г', color: '#9BE15D' },
  U_4909: { name: 'Клиент Д · тепловая генерация', short: 'Д', color: '#FF8A65' },
};

const LETTERS = 'АБВГДЕЖЗИКЛМНОПРСТУФ';
const PALETTE = ['#F5C451', '#7AC4FF', '#B9C2CC', '#9BE15D', '#FF8A65', '#C8A2FF'];

/** Демо-клиенты: разные отрасли, с кредитами и без, с ВЭД и без (см. КЛИЕНТЫ_ДЛЯ_ДЕМО). */
export const PREFERRED_COMPANY_IDS: string[] = (import.meta.env.VITE_COMPANY_IDS || Object.keys(DISPLAY).join(','))
  .split(',')
  .map((s: string) => s.trim())
  .filter(Boolean);

export const MAX_COMPANIES = 5;

export function companyDisplay(id: string, sector: string, index: number) {
  if (DISPLAY[id]) return DISPLAY[id];
  const letter = LETTERS[index % LETTERS.length];
  return { name: `Клиент ${letter} · ${sector}`, short: letter, color: PALETTE[index % PALETTE.length] };
}

/** Условное имя для ID из платежей/связей: свой демо-клиент или просто ID. */
export function knownCompanyName(id: string): string | null {
  return DISPLAY[id]?.name ?? null;
}
