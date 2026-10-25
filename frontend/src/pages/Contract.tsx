import { useState } from 'react';
import { api } from '../api';
import { rub } from '../lib/format';
import { useApp, useApplication } from '../app/context';
import { Button, Empty, Icon, Intro } from '../components/ui';

export function ContractPage() {
  const { products, go, run, refresh, notice } = useApp();
  const application = useApplication();
  const product = products.find((item) => item.id === application.productId);
  const [checked, setChecked] = useState(false);
  if (!application.decision?.approved)
    return (
      <Empty
        title="Договор недоступен"
        message="Договор доступен только по одобренной заявке."
        label="К заявке"
        onClick={() => go('application', application.id)}
      />
    );
  const accepted = ['OFFER_ACCEPTED', 'SIGNED_DEMO', 'DISBURSED_DEMO'].includes(application.status);
  const signed = ['SIGNED_DEMO', 'DISBURSED_DEMO'].includes(application.status);
  const accept = () =>
    run(async () => {
      if (!checked) throw new Error('Подтвердите ознакомление с условиями.');
      await api.acceptOffer(application.id);
      await refresh();
      notice('Демонстрационные условия приняты.');
    });
  const sign = () =>
    run(async () => {
      await api.signDemo(application.id);
      await refresh();
      notice('Демо-договор подписан, демонстрационная выдача выполнена.');
    });
  return (
    <>
      <div className="back-row">
        <a href={`#/result?id=${application.id}`}>
          <Icon name="back" size={16} /> К решению
        </a>
      </div>
      <Intro
        tag="ШАГ 03 / 03 · ОФОРМЛЕНИЕ"
        title={signed ? 'Демо-кредит оформлен' : 'Демонстрационный договор'}
        subtitle="Ознакомьтесь с условиями перед подтверждением."
      />
      {signed && (
        <div className="alert alert-success">
          <Icon name="check" size={21} />
          <div>
            <strong>Демонстрационное подписание и выдача завершены</strong>
            <p>Деньги не переводились. История действий сохранена в заявке.</p>
          </div>
        </div>
      )}
      <div className="contract-layout">
        <section className="panel contract-paper">
          <div className="contract-heading">
            <span className="brand-mark">А</span>
            <div>
              <span>АЛЬФА · ХАК</span>
              <small>ДЕМОНСТРАЦИОННЫЙ ДОКУМЕНТ</small>
            </div>
          </div>
          <div className="contract-rule" />
          <span className="section-label">ПРЕДЛОЖЕНИЕ № {application.id}</span>
          <h2>Условия кредитования</h2>
          <p className="muted">
            Этот документ создан для демонстрации интерфейса и не является кредитным договором или
            офертой.
          </p>
          <div className="contract-data">
            <div>
              <span>Заёмщик</span>
              <strong>{application.company.name}</strong>
            </div>
            <div>
              <span>ИНН</span>
              <strong>{application.company.inn}</strong>
            </div>
            <div>
              <span>Продукт</span>
              <strong>{product?.name}</strong>
            </div>
            <div>
              <span>Сумма кредита</span>
              <strong>{rub(application.need.amount)}</strong>
            </div>
            <div>
              <span>Срок</span>
              <strong>{application.need.term} мес.</strong>
            </div>
            <div>
              <span>Демоставка</span>
              <strong>{application.decision.rate}% годовых</strong>
            </div>
            <div>
              <span>Ориентир платежа</span>
              <strong>{rub(application.decision.payment)} / мес.</strong>
            </div>
            <div>
              <span>Досрочное погашение</span>
              <strong>Без комиссии в демосценарии</strong>
            </div>
          </div>
          <div className="contract-foot">
            <Icon name="shield" size={18} /> Прототип Альфа-Хак 2026 · Без юридической силы
          </div>
        </section>
        <aside className="panel contract-side">
          <span className="section-label">СЛЕДУЮЩИЙ ШАГ</span>
          <h3>{signed ? 'Готово!' : accepted ? 'Подпишите договор' : 'Подтвердите условия'}</h3>
          <p>
            {signed
              ? 'Вернитесь к заявке, чтобы посмотреть полную историю.'
              : 'Все действия на этой странице демонстрационные. Подтверждение не создаёт финансовых обязательств.'}
          </p>
          {!accepted ? (
            <>
              <label className="checkbox-line contract-check">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => setChecked(event.target.checked)}
                />
                <span>Я ознакомился с демонстрационными условиями</span>
              </label>
              <Button wide onClick={accept}>
                Принять условия <Icon name="arrow" size={17} />
              </Button>
            </>
          ) : !signed ? (
            <Button wide onClick={sign}>
              Подписать демо-договор <Icon name="arrow" size={17} />
            </Button>
          ) : (
            <Button variant="outline" wide onClick={() => go('application', application.id)}>
              История заявки <Icon name="arrow" size={17} />
            </Button>
          )}
        </aside>
      </div>
    </>
  );
}
