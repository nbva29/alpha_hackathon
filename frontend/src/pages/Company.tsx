import * as React from 'react';
import { api } from '../api';
import { rub } from '../lib/format';
import { useApp, useWorkspace, values } from '../app/context';
import { Button, Field, Icon, Intro, PanelHeading, SelectField } from '../components/ui';

export function CompanyPage() {
  const { run, refresh, notice } = useApp();
  const company = useWorkspace().company;
  const save = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    run(async () => {
      const data = values(form);
      await api.saveCompany({
        name: String(data.name),
        inn: String(data.inn),
        legalForm: String(data.legalForm),
        registeredAt: String(data.registeredAt),
        industry: String(data.industry),
        revenue: Number(data.revenue),
        expenses: Number(data.expenses),
        obligations: Number(data.obligations),
        overdue:
          form.elements.namedItem('overdue') instanceof HTMLInputElement &&
          (form.elements.namedItem('overdue') as HTMLInputElement).checked,
      });
      await refresh();
      notice('Данные компании сохранены.');
    });
  };
  return (
    <>
      <Intro
        tag="ПРОФИЛЬ БИЗНЕСА"
        title="Моя компания"
        subtitle="Сохранённые данные автоматически подставляются в новую заявку."
      />
      <div className="two-column">
        <section className="panel panel-form">
          <PanelHeading
            icon="building"
            title="Реквизиты и показатели"
            subtitle="Проверьте данные перед отправкой заявки"
          />
          <form className="form-stack" onSubmit={save}>
            <div className="field-grid">
              <Field
                name="name"
                label="Название компании"
                value={company?.name}
                placeholder="ООО «Пример»"
                required
              />
              <Field
                name="inn"
                label="ИНН"
                value={company?.inn}
                inputMode="numeric"
                maxLength={12}
                placeholder="10 или 12 цифр"
                required
              />
              <SelectField
                name="legalForm"
                label="Форма организации"
                value={company?.legalForm || 'ООО'}
                options={['ООО', 'ИП', 'АО'].map((value) => [value, value])}
              />
              <Field
                name="registeredAt"
                label="Дата регистрации"
                value={company?.registeredAt}
                type="date"
                required
              />
              <SelectField
                name="industry"
                label="Отрасль деятельности"
                value={company?.industry || 'Торговля'}
                options={[
                  'Торговля',
                  'Услуги',
                  'Производство',
                  'IT',
                  'Строительство',
                  'Другое',
                ].map((value) => [value, value])}
              />
              <Field
                name="revenue"
                label="Среднемесячная выручка, ₽"
                value={company?.revenue}
                type="number"
                min={0}
                required
              />
              <Field
                name="expenses"
                label="Среднемесячные расходы, ₽"
                value={company?.expenses}
                type="number"
                min={0}
                required
              />
              <Field
                name="obligations"
                label="Платежи по действующим кредитам, ₽"
                value={company?.obligations}
                type="number"
                min={0}
                required
              />
            </div>
            <label className="checkbox-line">
              <input type="checkbox" name="overdue" defaultChecked={company?.overdue} />
              <span>Есть просрочки по кредитам (демоданные)</span>
            </label>
            <div className="form-footer">
              <span>
                <Icon name="info" size={16} /> Изменения профиля не меняют уже отправленные заявки
              </span>
              <Button type="submit">
                Сохранить данные <Icon name="arrow" size={17} />
              </Button>
            </div>
          </form>
        </section>
        <aside className="side-stack">
          <div className="tip-card">
            <div className="tip-illustration">
              <Icon name="shield" size={34} />
            </div>
            <h3>Заполните один раз</h3>
            <p>
              При следующем оформлении данные компании уже будут в анкете. Перед отправкой их можно
              проверить и изменить.
            </p>
          </div>
          <div className="summary-card">
            <span>СВОБОДНЫЙ ДЕНЕЖНЫЙ ПОТОК</span>
            <strong>
              {rub(
                (company?.revenue || 0) - (company?.expenses || 0) - (company?.obligations || 0),
              )}
            </strong>
            <small>Выручка − расходы − обязательства</small>
          </div>
        </aside>
      </div>
    </>
  );
}
