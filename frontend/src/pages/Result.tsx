import { categoryNames } from '../mock-api';
import { rub } from '../lib/format';
import { useApp, useApplication } from '../app/context';
import { Button, Empty, Icon, Intro, PanelHeading } from '../components/ui';

export function ResultPage() {
  const { go, products } = useApp();
  const application = useApplication();
  const product = products.find((item) => item.id === application.productId);
  if (!application.decision)
    return (
      <>
        <div className="back-row">
          <a href={`#/application?id=${application.id}`}>
            <Icon name="back" size={16} /> К заявке
          </a>
        </div>
        <Empty
          title="Решение ещё не готово"
          message={
            application.status === 'DECISION_PENDING'
              ? 'Проверка завершена. Ожидаем решения сотрудника банка.'
              : 'Отправьте заявку для демонстрационной проверки.'
          }
          label="Открыть заявку"
          onClick={() => go('application', application.id)}
        />
      </>
    );
  const decision = application.decision;
  return (
    <>
      <div className="back-row">
        <a href={`#/application?id=${application.id}`}>
          <Icon name="back" size={16} /> К заявке
        </a>
      </div>
      <Intro
        tag={`РЕШЕНИЕ ПО ЗАЯВКЕ № ${application.id}`}
        title={decision.approved ? 'Хорошие новости!' : 'Решение по заявке'}
        subtitle={
          decision.approved
            ? 'Демонстрационная проверка завершена. Ознакомьтесь с условиями.'
            : 'Демонстрационная проверка завершена. Посмотрите причины решения.'
        }
      />
      <div className={`result-hero ${decision.approved ? 'approved-hero' : 'rejected-hero'}`}>
        <div className="result-symbol">
          <Icon name={decision.approved ? 'check' : 'info'} size={30} />
        </div>
        <div>
          <span>ДЕМОНСТРАЦИОННОЕ РЕШЕНИЕ</span>
          <h2>{decision.approved ? 'Заявка одобрена' : 'В заявке отказано'}</h2>
          <p>
            {decision.approved
              ? 'Условия рассчитаны по синтетическому каталогу для хакатона.'
              : 'Это результат локального симулятора. Можно изменить данные и создать новую заявку.'}
          </p>
        </div>
      </div>
      {decision.approved ? (
        <>
          <div className="result-grid">
            <div className="result-metric">
              <span>Сумма</span>
              <strong>{rub(application.need.amount)}</strong>
            </div>
            <div className="result-metric">
              <span>Срок</span>
              <strong>{application.need.term} мес.</strong>
            </div>
            <div className="result-metric">
              <span>Ставка</span>
              <strong>{decision.rate}%</strong>
            </div>
            <div className="result-metric">
              <span>Платёж / мес.</span>
              <strong>{rub(decision.payment)}</strong>
            </div>
          </div>
          <section className="panel result-details">
            <PanelHeading
              icon="file"
              title="Параметры предложения"
              subtitle={`${product?.name || ''} · ${product ? categoryNames[product.category] : ''}`}
            />
            <div className="detail-pair">
              <span>Назначение</span>
              <strong>{application.need.purpose}</strong>
            </div>
            <div className="detail-pair">
              <span>Компания</span>
              <strong>{application.company.name}</strong>
            </div>
            <div className="detail-pair">
              <span>Ориентир общей выплаты</span>
              <strong>{rub(decision.payment * application.need.term)}</strong>
            </div>
            <div className="panel-actions">
              <Button onClick={() => go('contract', application.id)}>
                Перейти к договору <Icon name="arrow" size={17} />
              </Button>
            </div>
          </section>
        </>
      ) : (
        <section className="panel result-details">
          <h2>Почему получен отказ</h2>
          <ul className="reason-list">
            {decision.reasons.map((reason) => (
              <li key={reason}>
                <Icon name="info" size={17} /> {reason}
              </li>
            ))}
          </ul>
          <p className="muted">
            Причины основаны на синтетических данных этого демо. Повторный подбор не гарантирует
            одобрения.
          </p>
          <Button onClick={() => go('need')}>
            Подобрать другое предложение <Icon name="arrow" size={17} />
          </Button>
        </section>
      )}
    </>
  );
}
