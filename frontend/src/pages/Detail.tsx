import * as React from "react";
import {
  saveDraft,
  submitApplication,
  evaluateProduct,
  statusNames,
} from "../mock-api";
import { day, productById } from "../lib/format";
import { useApp, useApplication, values } from "../app/context";
import {
  Button,
  Field,
  Icon,
  Intro,
  PanelHeading,
  StatusPill,
} from "../components/ui";
import { DocumentSection } from "../components/DocumentSection";

export function DetailPage() {
  const { userId, go, run, refresh, notice } = useApp();
  const application = useApplication();
  const product = productById(application.productId);
  if (!product) throw new Error("Предложение для заявки не найдено.");
  const editable =
    application.status === "DRAFT" || application.status === "NEEDS_INFO";
  const save = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = values(event.currentTarget);
    run(() => {
      const company = {
        ...application.company,
        name: String(data.name),
        inn: String(data.inn),
        registeredAt: String(data.registeredAt),
        revenue: Number(data.revenue),
        expenses: Number(data.expenses),
        obligations: Number(data.obligations),
      };
      const need = {
        ...application.need,
        category: product.category,
        purpose: String(data.purpose),
        amount: Number(data.amount),
        term: Number(data.term),
      };
      saveDraft(userId, application.id, { need, company });
      refresh();
      notice("Изменения в заявке сохранены.");
    });
  };
  const submit = () =>
    run(() => {
      const result = submitApplication(userId, application.id);
      refresh();
      if (result.status === "NEEDS_INFO")
        notice(
          "Для продолжения нужен документ. Причина указана в заявке.",
          true,
        );
      else {
        go("result", application.id);
        notice("Заявка передана сотруднику банка на рассмотрение.");
      }
    });
  const eligibility = evaluateProduct(
    product,
    application.need,
    application.company,
  );
  return (
    <>
      <div className="back-row">
        <a href="#/applications">
          <Icon name="back" size={16} /> К списку заявок
        </a>
      </div>
      <Intro
        tag={`ЗАЯВКА № ${application.id}`}
        title={editable ? "Проверьте заявку" : "Детали заявки"}
        subtitle={
          editable
            ? "Сведения сохраняются в черновике. После проверки отправьте заявку."
            : "Данные на момент отправки и история рассмотрения."
        }
        side={<StatusPill status={application.status} />}
      />
      <div className="detail-layout">
        <div className="detail-main">
          {editable && !eligibility.fits && (
            <div className="alert alert-warn" role="status">
              <Icon name="info" size={20} />
              <div>
                <strong>Перед отправкой исправьте параметры</strong>
                <p>
                  {eligibility.reasons.join(", ")}. Измените данные ниже и
                  сохраните черновик.
                </p>
              </div>
            </div>
          )}
          {application.status === "NEEDS_INFO" && (
            <div className="alert alert-warn">
              <Icon name="info" size={20} />
              <div>
                <strong>Нужны дополнительные сведения</strong>
                <p>
                  {application.history.at(-1)?.description}. Добавьте документ и
                  отправьте заявку повторно.
                </p>
              </div>
            </div>
          )}
          <section className="panel">
            <PanelHeading
              icon="wallet"
              title="Кредитная потребность"
              subtitle={`${product.name} · версия ${application.productVersion}`}
            />
            <form onSubmit={save}>
              <div className="field-grid">
                <Field
                  name="purpose"
                  label="Цель финансирования"
                  value={application.need.purpose}
                  disabled={!editable}
                  required
                />
                <Field
                  name="amount"
                  label="Сумма, ₽"
                  value={application.need.amount}
                  type="number"
                  min={1}
                  disabled={!editable}
                  required
                />
                <Field
                  name="term"
                  label="Срок, мес."
                  value={application.need.term}
                  type="number"
                  min={1}
                  disabled={!editable}
                  required
                />
              </div>
              <div className="subsection-title">Снимок данных компании</div>
              <div className="field-grid">
                <Field
                  name="name"
                  label="Название компании"
                  value={application.company.name}
                  disabled={!editable}
                  required
                />
                <Field
                  name="inn"
                  label="ИНН"
                  value={application.company.inn}
                  maxLength={12}
                  disabled={!editable}
                  required
                />
                <Field
                  name="registeredAt"
                  label="Дата регистрации"
                  value={application.company.registeredAt}
                  type="date"
                  disabled={!editable}
                  required
                />
                <Field
                  name="revenue"
                  label="Выручка в месяц, ₽"
                  value={application.company.revenue}
                  type="number"
                  min={0}
                  disabled={!editable}
                  required
                />
                <Field
                  name="expenses"
                  label="Расходы в месяц, ₽"
                  value={application.company.expenses}
                  type="number"
                  min={0}
                  disabled={!editable}
                  required
                />
                <Field
                  name="obligations"
                  label="Кредитные обязательства, ₽"
                  value={application.company.obligations}
                  type="number"
                  min={0}
                  disabled={!editable}
                  required
                />
              </div>
              {editable && (
                <Button type="submit" variant="outline">
                  Сохранить изменения
                </Button>
              )}
            </form>
          </section>
          <DocumentSection
            application={application}
            product={product}
            editable={editable}
          />
          {application.checks.length > 0 && (
            <section className="panel">
              <PanelHeading
                icon="shield"
                title="Результаты демопроверок"
                subtitle="История проверок доступна в этом кабинете"
              />
              {application.checks.map((check, index) => (
                <div className="check-block" key={index}>
                  <span>
                    Проверка {index + 1} · {day(check.date)}
                  </span>
                  <div>
                    <strong>ФНС</strong>
                    <span>{check.fns}</span>
                  </div>
                  <div>
                    <strong>БКИ</strong>
                    <span>{check.bki}</span>
                  </div>
                  <div>
                    <strong>Финансы</strong>
                    <span>{check.financial}</span>
                  </div>
                </div>
              ))}
            </section>
          )}
        </div>
        <aside className="detail-aside">
          <div className="panel status-panel">
            <span className="section-label">ТЕКУЩИЙ СТАТУС</span>
            <StatusPill status={application.status} />
            <h3>{statusNames[application.status]}</h3>
            <p>{application.history.at(-1)?.description}</p>
            {editable && (
              <Button wide onClick={submit}>
                {application.status === "NEEDS_INFO"
                  ? "Отправить повторно"
                  : "Отправить на проверку"}{" "}
                <Icon name="arrow" size={17} />
              </Button>
            )}
            {application.decision !== null && (
              <Button
                variant="outline"
                wide
                onClick={() => go("result", application.id)}
              >
                Посмотреть решение <Icon name="arrow" size={17} />
              </Button>
            )}
          </div>
          <div className="panel history-panel">
            <span className="section-label">ИСТОРИЯ ЗАЯВКИ</span>
            <div className="timeline">
              {[...application.history].reverse().map((event, index) => (
                <div
                  className={`timeline-item ${index === 0 ? "latest" : ""}`}
                  key={`${event.date}-${index}`}
                >
                  <span className="timeline-dot" />
                  <strong>{statusNames[event.status]}</strong>
                  <small>{day(event.date)}</small>
                  <p>{event.description}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
