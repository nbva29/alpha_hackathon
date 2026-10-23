import { products, evaluateProduct, monthlyPayment, type Product } from '../mock-api';
import { productById, rub } from '../lib/format';
import { useApp, useWorkspace } from '../app/context';
import { Button, Icon, Intro } from '../components/ui';
import { Wizard } from '../components/Wizard';
import { OfferCard } from '../components/OfferCard';

export function CatalogPage() {
  const { need, selected, setSelected, go } = useApp();
  const company = useWorkspace().company;
  const scored = products
    .map((product) => ({ product, ...evaluateProduct(product, need, company) }))
    .sort((a, b) => Number(b.fits) - Number(a.fits));
  const compared = selected.map(productById).filter((value): value is Product => Boolean(value));
  const best =
    compared.length > 1
      ? compared
          .filter((product) => evaluateProduct(product, need, company).fits)
          .sort(
            (a, b) =>
              monthlyPayment(need.amount, a.rate, need.term) -
              monthlyPayment(need.amount, b.rate, need.term),
          )[0]
      : undefined;
  return (
    <>
      <Intro
        tag="ШАГ 02 / 03 · ПРЕДЛОЖЕНИЯ"
        title="Подходящие решения"
        subtitle={`Нашли ${scored.filter((item) => item.fits).length} из ${products.length} демопредложений для вашей задачи.`}
        side={
          <Button variant="outline" onClick={() => go('need')}>
            <Icon name="back" size={16} /> Изменить параметры
          </Button>
        }
      />
      <Wizard step={2} />
      <div className="catalog-summary">
        <div>
          <Icon name="wallet" size={22} />
          <span>Ваша цель</span>
          <strong>{need.purpose}</strong>
        </div>
        <div>
          <span>Сумма</span>
          <strong>{rub(need.amount)}</strong>
        </div>
        <div>
          <span>Срок</span>
          <strong>{need.term} мес.</strong>
        </div>
      </div>
      <div className="section-head">
        <div>
          <h2>Каталог предложений</h2>
          <p>Синтетические условия для демонстрации; не являются действующими ставками банка</p>
        </div>
        <span className="result-count">{products.length} предложений</span>
      </div>
      <div className="offer-grid">
        {scored.map(({ product }) => (
          <OfferCard key={product.id} product={product} company={company} />
        ))}
      </div>
      {compared.length > 0 && (
        <section className="compare-panel">
          <div className="section-head">
            <div>
              <h2>Сравнение</h2>
              <p>Выбрано {compared.length} из 3 предложений</p>
              {best && (
                <p className="compare-explanation">
                  Выделен подходящий вариант с наименьшим расчётным платежом.
                </p>
              )}
              {compared.length > 1 && !best && (
                <p className="compare-explanation">
                  Среди выбранных предложений нет подходящих по заданным параметрам.
                </p>
              )}
            </div>
            <button type="button" className="text-button" onClick={() => setSelected([])}>
              Очистить
            </button>
          </div>
          <div className="compare-scroll">
            <table>
              <thead>
                <tr>
                  <th>Параметр</th>
                  {compared.map((item) => (
                    <th
                      key={item.id}
                      scope="col"
                      className={best?.id === item.id ? 'compare-best' : undefined}
                    >
                      {item.name}
                      {best?.id === item.id && (
                        <span className="compare-best-label">Лучший вариант</span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Соответствие</td>
                  {compared.map((item) => {
                    const evaluation = evaluateProduct(item, need, company);
                    return (
                      <td
                        key={item.id}
                        className={best?.id === item.id ? 'compare-best' : undefined}
                      >
                        {evaluation.fits ? 'Подходит' : evaluation.reasons.join(', ')}
                      </td>
                    );
                  })}
                </tr>
                <tr>
                  <td>Ставка</td>
                  {compared.map((item) => (
                    <td key={item.id} className={best?.id === item.id ? 'compare-best' : undefined}>
                      {item.rate}%
                    </td>
                  ))}
                </tr>
                <tr>
                  <td>Диапазон суммы</td>
                  {compared.map((item) => (
                    <td key={item.id} className={best?.id === item.id ? 'compare-best' : undefined}>
                      {rub(item.min)} – {rub(item.max)}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td>Срок</td>
                  {compared.map((item) => (
                    <td key={item.id} className={best?.id === item.id ? 'compare-best' : undefined}>
                      {item.minTerm}–{item.maxTerm} мес.
                    </td>
                  ))}
                </tr>
                <tr>
                  <td>Ориентир платежа</td>
                  {compared.map((item) => (
                    <td key={item.id} className={best?.id === item.id ? 'compare-best' : undefined}>
                      {rub(monthlyPayment(need.amount, item.rate, need.term))}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td>Доп. условия</td>
                  {compared.map((item) => (
                    <td key={item.id} className={best?.id === item.id ? 'compare-best' : undefined}>
                      {item.extras}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
