// Какие компании показывать в переключателе и как их называть.
// В датасете компании обезличены, поэтому названия вымышленные — только для демо.

const DISPLAY: Record<string, { name: string; short: string; color: string }> = {
  U_34911: { name: 'ООО «Южный зерновой терминал»', short: 'ЮЗТ', color: '#F5C451' },
  U_9250: { name: 'АО «Байкалинжстрой»', short: 'БИС', color: '#7AC4FF' },
  U_200890: { name: 'ООО «Уралметторг»', short: 'УМТ', color: '#B9C2CC' },
  U_102920: { name: 'ООО «Балтфуд Трейд»', short: 'БФТ', color: '#9BE15D' },
  U_4909: { name: 'АО «Столичная генерация»', short: 'СГ', color: '#FF8A65' },
};

const PALETTE = ['#F5C451', '#7AC4FF', '#B9C2CC', '#9BE15D', '#FF8A65', '#C8A2FF'];

/** Демо-клиенты: разные отрасли, с кредитами и без, с ВЭД и без (см. КЛИЕНТЫ_ДЛЯ_ДЕМО). */
export const PREFERRED_COMPANY_IDS: string[] = (import.meta.env.VITE_COMPANY_IDS || Object.keys(DISPLAY).join(','))
  .split(',')
  .map((s: string) => s.trim())
  .filter(Boolean);

export const MAX_COMPANIES = 5;

export function companyDisplay(id: string, sector: string, index: number) {
  if (DISPLAY[id]) return DISPLAY[id];
  const short = sector
    .split(/\s+/)
    .filter((w) => w.length > 2)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
  return {
    name: `Компания ${id} · ${sector}`,
    short: short || id.slice(-2),
    color: PALETTE[index % PALETTE.length],
  };
}
