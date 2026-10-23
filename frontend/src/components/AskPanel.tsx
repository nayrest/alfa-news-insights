import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '../api/client';
import type { ChatMessage, Insight } from '../api/types';
import { IconSend } from './Icons';
import { Drawer } from './TraceDrawer';

const SUGGESTIONS = [
  'Как это повлияет на нашу долговую нагрузку?',
  'Что делать в ближайший месяц?',
  'Покажи в разрезе нашей группы компаний',
];

export function AskPanel({ insight, onClose }: { insight: Insight; onClose: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (question: string) => {
    if (!question.trim() || loading) return;
    setMessages((m) => [...m, { role: 'user', text: question }]);
    setText('');
    setLoading(true);
    try {
      const answer = await api.ask(insight, question);
      setMessages((m) => [...m, answer]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: `Не удалось получить ответ: ${(e as Error).message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(text);
  };

  return (
    <Drawer title="Задать вопрос" subtitle={`По событию: ${insight.title}`} onClose={onClose}>
      <div className="chat">
        {messages.length === 0 && (
          <div className="chat__suggestions">
            {SUGGESTIONS.map((s) => <button key={s} className="chip-btn" onClick={() => send(s)}>{s}</button>)}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat__msg chat__msg--${m.role}`}>
            {m.text}
            {m.source_ids && m.source_ids.length > 0 && (
              <div className="chat__sources">
                Источник: {m.source_ids.map((id) => insight.sources.find((s) => s.id === id)?.title).filter(Boolean).join(', ')}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="chat__msg chat__msg--assistant chat__typing"><span /><span /><span /></div>}
        <div ref={endRef} />
      </div>
      <form className="chat__form" onSubmit={onSubmit}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Спросите о влиянии события на компанию" aria-label="Вопрос" />
        <button className="btn btn--primary btn--icon" disabled={!text.trim() || loading} aria-label="Отправить"><IconSend /></button>
      </form>
    </Drawer>
  );
}
