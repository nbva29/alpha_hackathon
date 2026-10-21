import { useState } from "react";
import {
  getAccount,
  getBankApplications,
  createDemoReviewApplication,
  reviewApplication,
  riskReasons,
  statusNames,
  type BankApplication,
  type Status,
} from "../mock-api";
import { day, initials, productById, rub } from "../lib/format";
import { Brand, Button, Icon, StatusPill } from "../components/ui";

type Filter = "pending" | "all" | "needs_info";

export function BankDashboard({
  userId,
  applicationId,
  go,
  run,
  refresh,
  notice,
  onLogout,
}: {
  userId: string;
  applicationId: string;
  go: (page: string, id?: string) => void;
  run: (action: () => void) => void;
  refresh: () => void;
  notice: (message: string, error?: boolean) => void;
  onLogout: () => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [comment, setComment] = useState("");
  const account = getAccount(userId);
  const applications = getBankApplications(userId);
  const visible = applications.filter((item) =>
    filter === "all"
      ? true
      : filter === "pending"
        ? item.application.status === "DECISION_PENDING"
        : item.application.status === "NEEDS_INFO",
  );
  const pending = applications.filter(
    (item) => item.application.status === "DECISION_PENDING",
  ).length;
  const needInfo = applications.filter(
    (item) => item.application.status === "NEEDS_INFO",
  ).length;
  const selected =
    applications.find((item) => item.application.id === applicationId) ||
    visible.find((item) => item.application.status === "DECISION_PENDING") ||
    visible[0];

  const decide = (action: "approve" | "reject" | "request_info") =>
    run(() => {
      if (!selected) return;
      reviewApplication(userId, selected.ownerId, selected.application.id, action, comment);
      setComment("");
      refresh();
      notice(
        action === "approve"
          ? "Заявка одобрена. Клиент увидит решение в своём кабинете."
          : action === "reject"
            ? "Отказ сохранён. Клиент увидит причину в своём кабинете."
            : "Клиенту отправлен запрос дополнительных сведений.",
      );
    });

  return (
    <div className="bank-shell">
      <aside className="bank-sidebar">
        <div className="brand"><Brand /></div>
        <span className="bank-sidebar-label">РАБОЧЕЕ МЕСТО БАНКА</span>
        <button
          type="button"
          className="bank-nav-link"
          onClick={() => {
            setFilter("all");
            go("bank");
          }}
        >
          <Icon name="file" size={20} /> Заявки на рассмотрении
          {pending > 0 && <b>{pending}</b>}
        </button>
        <div className="bank-sidebar-account">
          <span className="user-avatar">{initials(account.name)}</span>
          <span className="bank-account-info">
            <strong>{account.name}</strong>
            <small>Сотрудник банка</small>
          </span>
          <button
            className="icon-button"
            type="button"
            onClick={onLogout}
            aria-label="Выйти"
          >
            <Icon name="exit" size={18} />
          </button>
        </div>
      </aside>

      <main className="bank-main">
        <div className="bank-heading">
          <div>
            <span className="eyebrow">КРЕДИТНЫЙ ПРОЦЕСС · ДЕМО</span>
            <h1>Заявки клиентов</h1>
            <p>Проверяйте заявки, запрашивайте сведения и фиксируйте решение.</p>
          </div>
          <span className="bank-role-chip"><Icon name="shield" size={17} /> Кабинет сотрудника</span>
        </div>

        <div className="bank-stats">
          <div><span>На решении</span><strong>{pending}</strong></div>
          <div><span>Нужны сведения</span><strong>{needInfo}</strong></div>
          <div><span>Всего отправлено</span><strong>{applications.length}</strong></div>
        </div>

        <div className="bank-workspace">
          <section className="bank-queue panel" aria-label="Список заявок">
            <div className="bank-queue-head">
              <div><h2>Очередь заявок</h2><p>Заявки обоих демоклиентов</p></div>
              <span>{visible.length}</span>
            </div>
            <div className="bank-filters" role="group" aria-label="Фильтр заявок">
              {([
                ["pending", "На решении"],
                ["needs_info", "Нужны сведения"],
                ["all", "Все"],
              ] as [Filter, string][]).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={filter === value ? "active" : ""}
                  aria-pressed={filter === value}
                  onClick={() => setFilter(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            {visible.length ? (
              <div className="bank-list">
                {visible.map(({ application, borrowerName }) => (
                  <button
                    type="button"
                    key={application.id}
                    className={`bank-list-item ${selected?.application.id === application.id ? "active" : ""}`}
                    onClick={() => {
                      setComment("");
                      go("bank", application.id);
                    }}
                  >
                    <span className="bank-list-top"><strong>{application.company.name}</strong><StatusPill status={application.status} /></span>
                    <span>{borrowerName} · № {application.id}</span>
                    <span>{productById(application.productId)?.name || "Кредитное предложение"} · {rub(application.need.amount)}</span>
                    <small>Обновлено {day(application.updatedAt)}</small>
                    {application.status === "DECISION_PENDING" && (
                      <span className="bank-list-action">Рассмотреть заявку <Icon name="arrow" size={14} /></span>
                    )}
                  </button>
                ))}
              </div>
            ) : applications.length ? (
              <p className="bank-empty">В этом разделе заявок нет. Откройте вкладку «Все».</p>
            ) : (
              <div className="bank-empty">
                <p>Отправленных заявок пока нет. Вы можете создать и отправить заявку из кабинета клиента или добавить демонстрационную заявку для проверки интерфейса сотрудника.</p>
                <Button
                  small
                  onClick={() => run(() => {
                    const application = createDemoReviewApplication(userId);
                    refresh();
                    go("bank", application.id);
                    notice("Демонстрационная заявка создана и ожидает решения.");
                  })}
                >
                  Создать демозаявку
                </Button>
              </div>
            )}
          </section>

          <section className="bank-detail panel" aria-label="Рассмотрение заявки">
            {selected ? (
              <BankApplicationDetail
                item={selected}
                comment={comment}
                setComment={setComment}
                decide={decide}
              />
            ) : (
              <div className="bank-detail-empty">
                <Icon name="file" size={34} />
                <h2>Выберите заявку</h2>
                <p>Здесь появятся данные клиента, документы, результаты проверок и действия по заявке.</p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function BankApplicationDetail({
  item,
  comment,
  setComment,
  decide,
}: {
  item: BankApplication;
  comment: string;
  setComment: (value: string) => void;
  decide: (action: "approve" | "reject" | "request_info") => void;
}) {
  const { application, borrowerName } = item;
  const product = productById(application.productId);
  const risks = riskReasons(application);
  const disposable = application.company.revenue - application.company.expenses - application.company.obligations;
  const pending = application.status === "DECISION_PENDING";

  return (
    <>
      <div className="bank-detail-head">
        <div>
          <span className="section-label">ЗАЯВКА № {application.id}</span>
          <h2>{application.company.name}</h2>
          <p>{borrowerName} · ИНН {application.company.inn}</p>
        </div>
        <StatusPill status={application.status} />
      </div>
      {pending && (
        <div className="bank-decision">
          <h3>Принять решение по заявке</h3>
          <label htmlFor="bank-comment">Комментарий для клиента</label>
          <textarea
            id="bank-comment"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Для отказа или запроса сведений укажите причину"
            rows={3}
          />
          <p>Для отказа и запроса сведений комментарий обязателен. Одобрение доступно, если демопроверка не выявила рисков.</p>
          <div className="bank-actions">
            <Button onClick={() => decide("approve")} disabled={risks.length > 0}>Одобрить</Button>
            <Button variant="outline" onClick={() => decide("request_info")}>Запросить сведения</Button>
            <Button variant="outline" onClick={() => decide("reject")}>Отказать</Button>
          </div>
        </div>
      )}
      {application.status === "NEEDS_INFO" && (
        <div className="bank-waiting">
          <Icon name="clock" size={19} />
          <div>
            <strong>Ожидаем сведения от клиента</strong>
            <p>{application.history.at(-1)?.description}</p>
            <small>После повторной отправки с обязательным документом здесь появятся действия для принятия решения.</small>
          </div>
        </div>
      )}
      {application.decision && (
        <div className="bank-decision bank-decision-final">
          <h3>{application.decision.approved ? "Одобрено" : "Отказано"}</h3>
          <p>{application.decision.note}</p>
        </div>
      )}
      <div className="bank-detail-grid">
        <div><span>Продукт</span><strong>{product?.name || "—"}</strong></div>
        <div><span>Сумма</span><strong>{rub(application.need.amount)}</strong></div>
        <div><span>Срок</span><strong>{application.need.term} мес.</strong></div>
        <div><span>Ставка</span><strong>{product?.rate ?? "—"}%</strong></div>
        <div><span>Цель</span><strong>{application.need.purpose}</strong></div>
        <div><span>Свободный поток / мес.</span><strong>{rub(disposable)}</strong></div>
      </div>
      <div className="bank-section">
        <h3>Компания и проверка</h3>
        <div className="bank-facts">
          <p><span>Дата регистрации</span><strong>{day(application.company.registeredAt)}</strong></p>
          <p><span>Выручка / расходы</span><strong>{rub(application.company.revenue)} / {rub(application.company.expenses)}</strong></p>
          <p><span>Обязательства</span><strong>{rub(application.company.obligations)}</strong></p>
          <p><span>Просрочка</span><strong>{application.company.overdue ? "Есть" : "Нет"}</strong></p>
        </div>
        {application.checks.at(-1) && (
          <div className="bank-checks">
            <p><strong>ФНС</strong>{application.checks.at(-1)?.fns}</p>
            <p><strong>БКИ</strong>{application.checks.at(-1)?.bki}</p>
            <p><strong>Финансы</strong>{application.checks.at(-1)?.financial}</p>
          </div>
        )}
      </div>
      <div className="bank-section">
        <h3>Документы</h3>
        {application.documents.length ? (
          <div className="bank-documents">
            {application.documents.map((document) => (
              <a key={document.id} href={document.data} download={document.name}>
                <Icon name="file" size={17} /> {document.name} <small>Скачать</small>
              </a>
            ))}
          </div>
        ) : <p className="muted">Документы ещё не приложены.</p>}
      </div>
      <div className="bank-section">
        <h3>Оценка риска</h3>
        {risks.length ? (
          <ul className="bank-risks">{risks.map((reason) => <li key={reason}>{reason}</li>)}</ul>
        ) : <p className="bank-risk-ok"><Icon name="check" size={16} /> Предварительная проверка не выявила рисков.</p>}
      </div>
      <div className="bank-section">
        <h3>История статусов</h3>
        <ol className="bank-history">
          {[...application.history].reverse().map((event, index) => (
            <li key={`${event.date}-${index}`}>
              <strong>{statusNames[event.status as Status]}</strong>
              <span>{day(event.date)}</span>
              <p>{event.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </>
  );
}
