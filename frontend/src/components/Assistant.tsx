import { createContext, useContext } from "react";
import { useWorkspace } from "../app/context";
import { rub } from "../lib/format";
import { Icon } from "./ui";

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
  const company = useWorkspace().company;
  const questions = [
    [
      "Какие есть продукты?",
      "В каталоге шесть демопредложений: кредиты на развитие, оборотные средства и овердрафты. Выберите цель и сумму, чтобы увидеть подходящие варианты.",
    ],
    [
      "Какие данные нужны?",
      "Для заявки нужны сведения о компании, цель, сумма, срок и документ по правилам выбранного предложения.",
    ],
    [
      "Что означает статус?",
      "Статус показывает текущий этап обработки. История всех переходов находится в деталях заявки.",
    ],
  ];
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
            <span>Демо · справочная информация</span>
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
        <div className="assistant-body">
          <div className="assistant-bubble">
            <strong>Привет! 👋</strong>
            <p>
              Помогу сориентироваться в кредитном кабинете. Ответы основаны на
              демоданных приложения.
            </p>
          </div>
          <span className="assistant-label">ЧАСТЫЕ ВОПРОСЫ</span>
          {questions.map(([question, answer]) => (
            <details className="assistant-question" key={question}>
              <summary>
                {question} <Icon name="chevron" size={16} />
              </summary>
              <p>{answer}</p>
            </details>
          ))}
          <div className="assistant-context">
            <span>
              <Icon name="building" size={17} /> ВАША КОМПАНИЯ
            </span>
            <strong>{company?.name || "Профиль не заполнен"}</strong>
            <small>
              {company
                ? `Выручка ${rub(company.revenue)} в месяц`
                : "Откройте профиль, чтобы заполнить данные"}
            </small>
          </div>
        </div>
        <div className="assistant-foot">
          <Icon name="info" size={16} /> AI-модель не подключена. Основной
          сценарий доступен полностью.
        </div>
      </aside>
    </>
  );
}
