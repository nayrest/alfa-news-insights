import { useState } from 'react';
import type { Company, Counterparty } from '../api/types';
import { formatBillions, formatPercent } from '../utils/format';
import { CompanyAvatar } from './CompanySwitcher';
import { IconChevronDown } from './Icons';

const cpList = (list: Counterparty[]) =>
  list.slice(0, 3).map((c) => `${c.id} (${formatPercent(c.share)}, ${c.sector})`).join('; ');

// Профиль компании из df_Uid_data_hack.csv — то, на чём строится персонализация ленты.
export function CompanyProfile({ company }: { company: Company }) {
  const [open, setOpen] = useState(false);

  const tags = [
    company.has_loans ? 'Есть кредиты' : 'Без кредитов',
    company.fts_flag ? `ВЭД: ${company.fts_countries.join(', ') || 'есть'}` : 'Без ВЭД',
    company.client_type_label,
  ];

  const group = company.group;
  const rows: [string, string][] = [
    ['ID в датасете', company.id],
    ['Отрасль', `${company.sector} · ОКВЭД ${company.okved_code} — ${company.okved_name}`],
    ['Выручка', formatBillions(company.revenue)],
    ['Продукты банка', company.products.length ? company.products.join(', ') : 'нет'],
    ['Внешнеэкономическая деятельность', company.fts_flag ? company.fts_countries.join(', ') || 'есть' : 'нет данных ФТС'],
    ['Статус клиента', company.client_type_label],
    ['Стадия развития', company.eco_stage ?? 'нет данных'],
    ['Возраст компании', company.age ? `${company.age} лет` : 'нет данных'],
    ['Сотрудников (ФНС)', company.workers ?? 'нет данных'],
    ['Форма собственности', company.ownership ?? 'нет данных'],
    ['Регион', [company.region, company.city].filter(Boolean).join(', ') || 'нет данных'],
    [
      'Группа компаний',
      group.size > 1
        ? [`${group.size} юрлиц`, group.revenue && formatBillions(group.revenue), group.top_okved && `ОКВЭД: ${group.top_okved.join(', ')}`]
            .filter(Boolean)
            .join(' · ')
        : 'не входит в группу',
    ],
    ['Признак ключевого собственника', company.negative_mark ? 'есть' : 'нет'],
  ];
  if (company.market?.share != null) {
    rows.push([
      'Доля среди компаний с тем же ОКВЭД',
      `${formatPercent(company.market.share)} · место ${company.market.rank} из ${company.market.total} (по данным кейса)`,
    ]);
  }
  if (company.counterparties?.suppliers.length) rows.push(['Ключевые поставщики', cpList(company.counterparties.suppliers)]);
  if (company.counterparties?.buyers.length) rows.push(['Ключевые покупатели', cpList(company.counterparties.buyers)]);

  return (
    <section className={`profile${open ? ' profile--open' : ''}`}>
      <button className="profile__summary" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <CompanyAvatar short={company.short} color={company.color} size={44} />
        <div className="profile__main">
          <div className="profile__name">{company.name}</div>
          <div className="profile__line">
            {company.okved_name || company.sector} · {formatBillions(company.revenue)} · {company.region ?? ''}
          </div>
        </div>
        <div className="profile__tags">
          {tags.map((t) => <span key={t} className="tag">{t}</span>)}
        </div>
        <span className="profile__toggle">
          {open ? 'Скрыть' : 'Профиль компании'} <IconChevronDown width={16} height={16} />
        </span>
      </button>
      {open && (
        <div className="profile__details">
          <p className="profile__hint">Эти признаки агент использует, чтобы отобрать события и объяснить их влияние именно на вашу компанию.</p>
          <dl>
            {rows.map(([k, v]) => (
              <div key={k} className="profile__row"><dt>{k}</dt><dd>{v}</dd></div>
            ))}
          </dl>
        </div>
      )}
    </section>
  );
}
