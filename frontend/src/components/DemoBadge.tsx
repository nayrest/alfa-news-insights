import { USE_MOCKS } from '../api/client';

// На показе моки нельзя спутать с живым агентом: жюри проверяет, что нет заготовленных сценариев.

/** Полоса под шапкой на всех экранах, пока включён VITE_USE_MOCKS=true. */
export function DemoBanner() {
  if (!USE_MOCKS) return null;
  return (
    <div className="demo-banner" role="status">
      <b>Демо-данные.</b> Интерфейс работает на заготовленных примерах, а не на ответах AI-агента.
      Для живого режима выключите <code>VITE_USE_MOCKS</code>.
    </div>
  );
}

/** Метка на карточках с демо-содержимым. */
export function DemoBadge() {
  if (!USE_MOCKS) return null;
  return <span className="demo-badge" title="Заготовленный пример, не ответ AI-агента">Демо-данные</span>;
}
