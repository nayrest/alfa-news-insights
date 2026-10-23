import { useEffect, useRef, useState } from 'react';
import { useCompany } from '../state/CompanyContext';
import { formatBillions } from '../utils/format';
import { IconCheck, IconChevronDown } from './Icons';

export function CompanyAvatar({ short, color, size = 36 }: { short: string; color: string; size?: number }) {
  return (
    <span className="company-avatar" style={{ background: color, width: size, height: size, fontSize: size * 0.33 }}>
      {short}
    </span>
  );
}

export function CompanySwitcher() {
  const { companies, current, select } = useCompany();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  if (!current) return <div className="company-switcher skeleton" />;

  return (
    <div className="company-switcher" ref={ref}>
      <button className="company-switcher__btn" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="listbox">
        <CompanyAvatar short={current.short} color={current.color} />
        <span className="company-switcher__text">
          <span className="company-switcher__name">{current.name}</span>
          <span className="company-switcher__sub">{[current.id, current.city].filter(Boolean).join(' · ')}</span>
        </span>
        <IconChevronDown width={16} height={16} />
      </button>
      {open && (
        <ul className="company-switcher__menu" role="listbox">
          <li className="company-switcher__caption">Компании, к которым у вас есть доступ</li>
          {companies.map((c) => (
            <li key={c.id}>
              <button
                role="option"
                aria-selected={c.id === current.id}
                className="company-switcher__option"
                onClick={() => {
                  select(c.id);
                  setOpen(false);
                }}
              >
                <CompanyAvatar short={c.short} color={c.color} size={32} />
                <span className="company-switcher__text">
                  <span className="company-switcher__name">{c.name}</span>
                  <span className="company-switcher__sub">{formatBillions(c.revenue)} · {c.okved_name || c.sector}</span>
                </span>
                {c.id === current.id && <IconCheck className="company-switcher__check" />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
