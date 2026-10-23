import * as React from 'react';
import { categoryNames, ageMonths, type Category } from '../mock-api';
import { rub } from '../lib/format';
import { useApp, useWorkspace, values } from '../app/context';
import { Button, Field, Icon, Intro, PanelHeading, SelectField } from '../components/ui';
import { Wizard } from '../components/Wizard';

export function NeedPage() {
  const { need, setNeed, go } = useApp();
  const company = useWorkspace().company;
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = values(event.currentTarget);
    setNeed({
      purpose: String(data.purpose),
      category: String(data.category) as Category,
      amount: Number(data.amount),
      term: Number(data.term),
    });
    go('catalog');
  };
  return (
    <>
      <Intro
        tag="ШАГ 01 / 03 · ПОДБОР"
        title="Какую задачу решаем?"
        subtitle="Расскажите о потребности — мы покажем подходящие демопредложения."
      />
      <Wizard step={1} />
      <div className="two-column">
        <section className="panel panel-form">
          <PanelHeading
            icon="wallet"
            title="Параметры финансирования"
            subtitle="Подбор рассчитывается по понятным правилам"
          />
          <form className="form-stack" onSubmit={submit}>
            <Field
              name="purpose"
              label="На что нужны деньги?"
              value={need.purpose}
              placeholder="Например, закупка оборудования"
              required
            />
            <SelectField
              name="category"
              label="Тип финансирования"
              value={need.category}
              options={Object.entries(categoryNames)}
            />
            <div className="field-grid">
              <Field
                name="amount"
                label="Желаемая сумма, ₽"
                value={need.amount}
                type="number"
                min={100000}
                step={10000}
                required
              />
              <SelectField
                name="term"
                label="Срок, месяцев"
                value={need.term}
                options={['3', '6', '12', '18', '24', '36', '48', '60'].map((value) => [
                  value,
                  `${value} мес.`,
                ])}
              />
            </div>
            <Button type="submit" wide>
              Показать предложения <Icon name="arrow" size={19} />
            </Button>
          </form>
        </section>
        <aside className="side-stack">
          <div className="tip-card dark-tip">
            <span>
              <Icon name="spark" size={24} />
            </span>
            <h3>Подбор без ожидания</h3>
            <p>Оценим сумму, срок и параметры компании. Всё работает локально и без AI.</p>
          </div>
          <div className="mini-company">
            <div>
              <span className="mini-company-icon">
                <Icon name="building" />
              </span>
              <strong>{company?.name || 'Профиль не заполнен'}</strong>
            </div>
            <p>
              {company
                ? `Срок работы: ${Math.floor(ageMonths(company.registeredAt) / 12)} г. ${ageMonths(company.registeredAt) % 12} мес. · Выручка ${rub(company.revenue)} / мес.`
                : 'Для оформления заявки потребуется заполнить сведения о компании.'}
            </p>
            <a href="#/company">
              {company ? 'Изменить сведения' : 'Заполнить профиль'} <Icon name="arrow" size={15} />
            </a>
          </div>
        </aside>
      </div>
    </>
  );
}
