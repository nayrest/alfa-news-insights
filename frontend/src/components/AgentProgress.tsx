import { useEffect, useState } from 'react';
import type { FeedItem } from '../api/types';
import { IconCheck } from './Icons';

// Шаги совпадают с backend/app/agent/runner.py. Бэкенд отвечает одним запросом,
// поэтому прогресс условный: показываем, чем агент занят, пока ждём ответ.
const STEPS = [
  'Сопоставляем событие с признаками компании',
  'Планируем анализ',
  'Ищем позицию Альфа-Банка в аналитике',
  'Готовим черновик интерпретации',
  'Самопроверка: источники и непротиворечивость',
];

export function AgentProgress({ item }: { item: FeedItem }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    // Если разбор уже есть в кэше бэкенда, ответ придёт раньше, чем сменится первый шаг.
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 4000);
    return () => clearInterval(timer);
  }, [item.id]);

  return (
    <article className="detail agent-progress">
      <h1 className="detail__title">{item.title}</h1>
      <p className="detail__lead">{item.lead}</p>
      <div className="agent-progress__box">
        <div className="agent-progress__head">AI-агент готовит разбор для вашей компании…</div>
        <ol className="agent-progress__steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i < step ? 'done' : i === step ? 'active' : ''}>
              <span className="agent-progress__dot">{i < step ? <IconCheck width={14} height={14} /> : i + 1}</span>
              {s}
            </li>
          ))}
        </ol>
        {item.insight_id === null && <p className="muted agent-progress__note">Первый разбор события занимает до минуты, потом он сохраняется.</p>}
      </div>
    </article>
  );
}
