import { InsightsWidget } from '../components/InsightsWidget';
import { IconChevron, IconClose, IconDoc, IconEye, IconList, IconPlus, IconSettings, IconUpload } from '../components/Icons';

// Главная Альфа-Бизнеса: всё, кроме виджета инсайтов, — статика для контекста точки входа.
const TASKS = [
  ['Подписать и отправить', 1, true],
  ['В работе у банка', 7, true],
  ['Отклонённые', 4, true],
  ['Черновики', 1, false],
  ['Оплатить', 1, false],
  ['Доработать', 0, false],
  ['Принять предложение', 3, false],
] as const;

export function HomePage() {
  return (
    <div className="home">
      <div className="quick-actions">
        <button className="btn btn--white"><IconDoc /> Скачать выписку</button>
        <button className="btn btn--white"><IconUpload /> Импорт платежей</button>
        <button className="btn btn--white"><IconPlus /> Создать платёж</button>
        <button className="btn btn--grey">Ещё</button>
      </div>

      <section className="hero">
        <div className="hero__balance">
          <div className="hero__amount">2 524 550 000,00 RUB</div>
          <div className="hero__overdraft">↳ 10 800 570 344,95 RUB с овердрафтом</div>
          <div className="hero__currencies">
            <span>4 000,00 CNY</span><span className="dot">·</span><span>40 000,00 KZT</span><span className="dot">·</span><span className="chip-dark">+5</span>
          </div>
          <div className="hero__promo">
            <span className="hero__promo-dot">+</span> Переводите себе бесплатно <b>5 000 000 ₽</b>
            <span className="chip-green">ОДОБРЕНО</span>
            <IconClose className="hero__promo-close" width={16} height={16} />
          </div>
          <div className="hero__links">
            <div className="hero__link"><span className="hero__link-icon"><IconList /></span><div>Счета<small>8 в рублях, 2 в валюте</small></div></div>
            <div className="hero__link"><span className="hero__link-icon"><IconPlus /></span><div>Заказать<br />бизнес-карту</div></div>
          </div>
        </div>
        <div className="hero__tasks">
          <h3>Дела в работе</h3>
          <ul>
            {TASKS.map(([label, n, red]) => (
              <li key={label} className={n === 0 ? 'muted' : ''}>
                {label} <span className={`count${red ? ' count--red' : ''}`}>{n}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="hero__promo-card">
          <h3>Умная карта для всех</h3>
          <p>Кэшбэк, бонусы и удобные платежи</p>
          <div className="hero__card-art" aria-hidden>1010 0 1010 0</div>
        </div>
        <div className="hero__footer"><span>Реквизиты</span><span>Тариф</span></div>
      </section>

      <div className="tabs-row">
        <nav className="tabs">
          <span className="tabs__item tabs__item--active">Сводка</span>
          <span className="tabs__item">Счета на главной</span>
          <span className="tabs__item">Мультибанк</span>
          <span className="tabs__item">Металлы</span>
        </nav>
        <div className="tabs-row__tools">
          <span className="toggle"><span className="toggle__on"><IconEye width={18} height={18} /></span><span><IconEye width={18} height={18} /></span></span>
          <IconSettings />
        </div>
      </div>

      <div className="summary-grid">
        <section className="card">
          <header className="card__header">
            <span className="card__title">Активные заявки <span className="count">9</span></span>
            <IconChevron />
          </header>
          <div className="request">
            <div className="request__name">Лизинг</div>
            <div className="request__row"><b>75 000 ₽</b><span className="chip-blue">НА ПОДПИСЬ</span></div>
            <div className="request__row muted"><span>09.04.2026</span><span>2 из 5</span></div>
          </div>
          <div className="request">
            <div className="request__name">Факторинг</div>
            <div className="request__row"><b>1 200 000 ₽</b><span className="chip-grey">НА ПРОВЕРКЕ</span></div>
            <div className="request__row muted"><span>02.04.2026</span><span>3 из 5</span></div>
          </div>
          <div className="request">
            <div className="request__name">Кредит на развитие</div>
            <div className="request__row"><b>50 000 000 ₽</b><span className="chip-grey">ЧЕРНОВИК</span></div>
            <div className="request__row muted"><span>28.03.2026</span><span>1 из 5</span></div>
          </div>
        </section>

        <InsightsWidget />

        <div className="stories">
          <div className="story story--dark">Как получить деньги на бизнес</div>
          <div className="story story--red">Альфа-Саммит</div>
        </div>
      </div>
    </div>
  );
}
