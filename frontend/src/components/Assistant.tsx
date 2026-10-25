import { createContext, useContext, useState, type FormEvent } from 'react';
import { api, type AssistantReply } from '../api';
import { useApp, useWorkspace } from '../app/context';
import { rub } from '../lib/format';
import { Icon } from './ui';

function MessageText({ text }: { text: string }) {
  return <div className="assistant-message-text">{text.split('\n').map((line, lineIndex) => (
    <p key={lineIndex}>{line.split(/(\*\*[^*]+\*\*)/g).map((part, partIndex) =>
      part.startsWith('**') && part.endsWith('**')
        ? <strong key={partIndex}>{part.slice(2, -2)}</strong>
        : part,
    )}</p>
  ))}</div>;
}

export const AssistantContext = createContext<() => void>(() => {});
export function AssistantToggle() {
  const toggle = useContext(AssistantContext);
  return (
    <button type="button" className="text-button" onClick={toggle}>
      Открыть помощника <Icon name="arrow" size={15} />
    </button>
  );
}
export function Assistant({ close }: { close: () => void }) {
  const { route, selected, need } = useApp();
  const company = useWorkspace().company;
  const [messages, setMessages] = useState<
    { role: 'user' | 'assistant'; text: string; sources?: string[]; mode?: string; alternatives?: AssistantReply['alternatives'] }[]
  >([
    {
      role: 'assistant',
      text: 'Привет! Спросите о кредитных продуктах, документах или статусе заявки.',
    },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setMessages((current) => [...current, { role: 'user', text: question }]);
    setInput('');
    setBusy(true);
    try {
      const reply = await api.assistant(
        question,
        ['application', 'result', 'contract'].includes(route.page) ? route.id : undefined,
        { page: route.page, selected_product_ids: selected, need },
        messages.slice(-6).map(({ role, text }) => ({ role, text })),
      );
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: reply.answer,
          sources: reply.sources?.map((source) => source.name) || [],
          mode: reply.mode,
          alternatives: reply.alternatives,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: error instanceof Error ? error.message : 'Не удалось получить ответ.',
        },
      ]);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="assistant-scrim" onClick={close} />
      <aside className="assistant-panel" aria-label="Помощник">
        <div className="assistant-head">
          <div className="assistant-orb">
            <Icon name="spark" size={22} />
          </div>
          <div>
            <strong>Помощник</strong>
            <span>Каталог кредитов и заявки</span>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={close}
            aria-label="Закрыть помощника"
          >
            <Icon name="close" size={19} />
          </button>
        </div>
        <div className="assistant-body" aria-live="polite">
          {messages.map((message, index) => (
            <div
              className={`assistant-bubble ${message.role === 'user' ? 'assistant-user' : ''}`}
              key={index}
            >
              <span className="assistant-message-role">{message.role === 'user' ? 'Вы' : 'Помощник'}</span>
              <MessageText text={message.text} />
              {message.mode && (
                <small>
                  {message.mode === 'local-llm'
                    ? 'Ответ настроенной ИИ-модели'
                    : message.mode === 'verified-comparison'
                    ? 'Проверенное сравнение по условиям каталога'
                    : 'Справочный ответ без модели'}
                </small>
              )}
              {message.sources && message.sources.length > 0 && (
                <small>Источники: {message.sources.join(', ')}</small>
              )}
              {message.alternatives && message.alternatives.length > 0 && (
                <div className="assistant-alternatives">
                  <strong>Другие варианты</strong>
                  {message.alternatives.map((item) => (
                    <div className="assistant-alternative" key={item.product.id}>
                      <b>{item.product.name}</b>
                      <span>Плюсы: {item.pros.join('; ')}</span>
                      <span>Минусы и условия: {item.cons.join('; ')}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className="assistant-bubble">
              <span className="assistant-message-role">Помощник</span>
              <MessageText text="Формирую ответ…" />
            </div>
          )}
          <div className="assistant-context">
            <span>
              <Icon name="building" size={17} /> ВАША КОМПАНИЯ
            </span>
            <strong>{company?.name || 'Профиль не заполнен'}</strong>
            <small>
              {company
                ? `Выручка ${rub(company.revenue)} в месяц`
                : 'Откройте профиль, чтобы заполнить данные'}
            </small>
          </div>
        </div>
        <form className="assistant-input" onSubmit={submit}>
          <input
            aria-label="Вопрос помощнику"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Спросите о кредите…"
            maxLength={3000}
            disabled={busy}
          />
          <button type="submit" disabled={busy || !input.trim()} aria-label="Отправить вопрос">
            <Icon name="arrow" size={18} />
          </button>
        </form>
        <div className="assistant-foot">
          <Icon name="info" size={16} /> Ответы справочные; решение формируют правила кредитного
          конвейера.
        </div>
      </aside>
    </>
  );
}
