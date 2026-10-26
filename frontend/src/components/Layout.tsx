import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { CompanySwitcher } from './CompanySwitcher';
import { DemoBanner } from './DemoBadge';
import { ErrorBoundary } from './ErrorBoundary';
import {
  IconBell, IconCard, IconClock, IconDoc, IconGov, IconGrid, IconInbox, IconList, IconMail, IconPlus,
  IconSettings, IconSpark, IconUpload, IconUsers,
} from './Icons';

const MENU = [
  { to: '/requests', label: 'Заявки', icon: IconDoc, badge: 'НОВОЕ' },
  { to: '/payment', label: 'Новый платёж', icon: IconPlus },
  { to: '/insights', label: 'Новостные инсайты', icon: IconSpark, badge: 'НОВОЕ', highlight: true },
  { to: '/feed', label: 'Лента операций', icon: IconInbox },
  { to: '/in-progress', label: 'Платежи в работе', icon: IconClock },
  { to: '/import', label: 'Импорт реестров', icon: IconUpload },
  { to: '/statement', label: 'Выписка', icon: IconDoc },
  { to: '/accounts', label: 'Счета', icon: IconList },
  { to: '/counterparties', label: 'Контрагенты', icon: IconUsers },
  { to: '/certificates', label: 'Справки', icon: IconDoc },
  { to: '/invoices', label: 'Счета на оплату', icon: IconList },
  { to: '/cards', label: 'Карты', icon: IconCard },
];

export function Layout() {
  const location = useLocation();
  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="logo">
          <span className="logo__mark">А</span>
          <span className="logo__text">Альфа-Бизнес</span>
        </NavLink>
        <div className="topbar__right">
          <button className="icon-btn" aria-label="Сообщения"><IconMail /></button>
          <button className="icon-btn" aria-label="Уведомления"><IconBell /></button>
          <CompanySwitcher />
          <span className="boss-pill">Альфа Босс</span>
        </div>
      </header>

      <aside className="sidebar">
        <NavLink to="/" end className="sidebar__item sidebar__item--all">
          <IconGrid /> <span>Все сервисы</span>
        </NavLink>
        <hr />
        {MENU.map(({ to, label, icon: Icon, badge, highlight }) => (
          <NavLink key={to} to={to} className={`sidebar__item${highlight ? ' sidebar__item--highlight' : ''}`}>
            <Icon /> <span>{label}</span>
            {badge && <span className="badge-new">{badge}</span>}
          </NavLink>
        ))}
        <hr />
        <NavLink to="/goszakupki" className="sidebar__item"><IconGov /> <span>Госзакупки</span></NavLink>
        <div className="sidebar__spacer" />
        <button className="sidebar__item sidebar__item--muted"><IconSettings /> <span>Настроить меню</span></button>
      </aside>

      <main className="content">
        <DemoBanner />
        <ErrorBoundary key={location.pathname.split('/')[1]}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
