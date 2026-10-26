import { useState } from 'react';
import type { Company, Counterparty } from '../api/types';
import { knownCompanyName } from '../config/companies';
import { formatBillions, formatPercent } from '../utils/format';
import { CompanyAvatar } from './CompanySwitcher';
import { IconChevronDown } from './Icons';

function CounterpartyList({ title, hint, items }: { title: string; hint: string; items: Counterparty[] }) {
  return (
    <div className="cp-list">
      <h4>{title} <span className="muted">{hint}</span></h4>
      {items.length === 0 ? (
        <p className="muted cp-list__empty">Нет данных о платежах</p>
      ) : (
        <ul>
          {items.map((c) => (
            <li key={c.id}>
              <div className="cp-list__row">
                <span className="cp-list__name" title={c.id}>{knownCompanyName(c.id) ?? c.id}</span>
                <span className="cp-list__share">{formatPercent(c.share)}</span>
              </div>
              <div className="cp-list__bar"><span style={{ width: `${Math.max(c.share * 100, 2)}%` }} /></div>
              <div className="muted cp-list__sector">{c.sector}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Профиль компании из данных кейса — то, на чём строится персонализация ленты.
export function CompanyProfile({ company }: { company: Company }) {
  const [open, setOpen] = useState(false);
  const countries = company.fts_countries;

  const tags = [
    company.has_loans ? 'Есть кредиты' : 'Без кредитов',
    company.fts_flag
      ? `ВЭД: ${countries.slice(0, 2).join(', ') || 'есть'}${countries.length > 2 ? ` +${countries.length - 2}` : ''}`
      : 'Без ВЭД',
    company.client_type_label,
  ];

  const group = company.group;
  const rows: [string, string][] = [
    ['ID в датасете', company.id],
    ['Отрасль', `${company.sector} · ОКВЭД ${company.okved_code} — ${company.okved_name}`],
    ['Выручка', formatBillions(company.revenue)],
    ['Продукты банка', company.products.length ? company.products.join(', ') : 'нет'],
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
  if (company.linked_companies?.length) {
    rows.push(['Связанные через физлиц', `${company.linked_companies.length} компаний`]);
  }

  const cps = company.counterparties;

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
          <p className="profile__hint">
            Эти признаки агент использует, чтобы отобрать события и объяснить их влияние именно на вашу компанию.
            Название условное: данные кейса обезличены.
          </p>
          <dl>
            {rows.map(([k, v]) => (
              <div key={k} className="profile__row"><dt>{k}</dt><dd>{v}</dd></div>
            ))}
          </dl>

          <h3 className="profile__subtitle">Внешнеэкономическая деятельность</h3>
          {company.fts_flag && countries.length > 0 ? (
            <div className="country-chips">
              {countries.map((c) => <span key={c} className="tag tag--country">{c}</span>)}
            </div>
          ) : (
            <p className="muted">{company.fts_flag ? 'Ведёт ВЭД, страны не указаны' : 'Нет данных ФТС о ВЭД'}</p>
          )}

          {cps && (
            <>
              <h3 className="profile__subtitle">Ключевые контрагенты по платежам</h3>
              <div className="cp-grid">
                <CounterpartyList title="Поставщики" hint="кому платит компания" items={cps.suppliers} />
                <CounterpartyList title="Покупатели" hint="кто платит компании" items={cps.buyers} />
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
