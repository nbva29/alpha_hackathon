import * as React from 'react';
import { api } from '../api';
import type { Application, Product } from '../mock-api';
import { day } from '../lib/format';
import { useApp } from '../app/context';
import { Icon, PanelHeading } from './ui';

export function DocumentSection({
  application,
  product,
  editable,
}: {
  application: Application;
  product: Product;
  editable: boolean;
}) {
  const { run, refresh, notice } = useApp();
  const label = product.document === 'statement' ? 'Выписка по счёту' : 'Финансовая отчётность';
  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      if (
        !['application/pdf', 'image/png', 'image/jpeg'].includes(file.type) ||
        file.size > 1024 * 1024
      )
        throw new Error('Загрузите PDF, PNG или JPG размером до 1 МБ.');
      await api.uploadDocument(application.id, product.document, file);
      await refresh();
      notice('Документ добавлен к заявке.');
    } catch (error) {
      notice(error instanceof Error ? error.message : 'Не удалось загрузить документ.', true);
    }
  };
  return (
    <section className="panel documents-panel">
      <PanelHeading icon="file" title="Документы" subtitle={`Обязательный документ: ${label}`} />
      {editable && (
        <label className="upload-zone">
          <Icon name="upload" size={24} />
          <strong>Добавить {label.toLowerCase()}</strong>
          <span>PDF, PNG или JPG до 1 МБ</span>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            hidden
            onChange={upload}
          />
        </label>
      )}
      {application.documents.length ? (
        <div className="document-list">
          {application.documents.map((document) => (
            <div className="document-row" key={document.id}>
              <Icon name="file" size={18} />
              <span className="document-info">
                <strong>{document.name}</strong>
                <small>
                  {Math.round(document.size / 1024)} КБ · {day(document.addedAt)}
                </small>
              </span>
              {editable && (
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Удалить документ"
                  onClick={() =>
                    run(async () => {
                      await api.deleteDocument(application.id, document.id);
                      await refresh();
                      notice('Документ удалён.');
                    })
                  }
                >
                  <Icon name="close" size={17} />
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Документ пока не добавлен.</p>
      )}
      {editable && (
        <p className="document-note">
          <Icon
            name={
              application.documents.some((item) => item.kind === product.document)
                ? 'check'
                : 'info'
            }
            size={16}
          />{' '}
          {application.documents.some((item) => item.kind === product.document)
            ? 'Обязательный документ загружен'
            : 'При отправке без документа симулятор запросит его дополнительно'}
        </p>
      )}
    </section>
  );
}
