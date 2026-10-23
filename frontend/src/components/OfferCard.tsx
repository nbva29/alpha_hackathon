import {
  createApplication,
  evaluateProduct,
  categoryNames,
  type Product,
  type Company,
} from '../mock-api';
import { rub } from '../lib/format';
import { useApp } from '../app/context';
import { Button, Icon } from './ui';

export function OfferCard({ product, company }: { product: Product; company: Company | null }) {
  const { userId, need, selected, setSelected, go, run, notice } = useApp();
  const result = evaluateProduct(product, need, company);
  const compared = selected.includes(product.id);
  const choose = () =>
    run(() => {
      const application = createApplication(userId, need, product.id);
      go('application', application.id);
      notice('Черновик заявки создан.');
    });
  return (
    <article className={`offer-card ${result.fits ? '' : 'offer-muted'}`}>
      <div className="offer-head">
        <span className="offer-category">{categoryNames[product.category]}</span>
        <span className="offer-id">{product.version}</span>
      </div>
      <div className="offer-title-row">
        <div>
          <h3>{product.name}</h3>
          <p>{product.purpose}</p>
        </div>
        <div className="offer-glyph">
          <Icon name={product.category === 'overdraft' ? 'wallet' : 'arrow'} size={21} />
        </div>
      </div>
      <div className="offer-metrics">
        <div>
          <span>Ставка от</span>
          <strong>{product.rate.toLocaleString('ru-RU')}%</strong>
        </div>
        <div>
          <span>Сумма</span>
          <strong>
            {rub(product.min)}–{rub(product.max)}
          </strong>
        </div>
        <div>
          <span>Срок</span>
          <strong>
            {product.minTerm}–{product.maxTerm} мес.
          </strong>
        </div>
      </div>
      <div className="offer-terms">
        <span>
          <Icon name="check" size={16} /> {product.limit}
        </span>
        <span>
          <Icon name="check" size={16} /> {product.extras}
        </span>
      </div>
      <div className="offer-footer">
        {result.fits ? (
          <span className="fit-label">
            <Icon name="check" size={16} /> Подходит по параметрам
          </span>
        ) : (
          <span className="unfit-label">
            <Icon name="info" size={16} /> {result.reasons.join(', ')}
          </span>
        )}
        <div>
          <Button
            variant="outline"
            small
            onClick={() =>
              setSelected((current) =>
                compared
                  ? current.filter((id) => id !== product.id)
                  : [...current.slice(-2), product.id],
              )
            }
          >
            {compared ? 'Убрать из сравнения' : 'Сравнить'}
          </Button>
          <Button small onClick={choose}>
            Выбрать <Icon name="arrow" size={16} />
          </Button>
        </div>
      </div>
    </article>
  );
}
