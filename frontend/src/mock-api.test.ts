import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  login,
  getWorkspace,
  saveCompany,
  createApplication,
  getApplication,
  addDocument,
  submitApplication,
  acceptOffer,
  signDemo,
  products,
  saveDraft,
  evaluateProduct,
  getBankApplications,
  getBankApplication,
  reviewApplication,
  riskReasons,
  getSession,
  createDemoReviewApplication,
} from './mock-api.ts';

const memory = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
};
beforeEach(() => {
  globalThis.localStorage = memory();
  globalThis.sessionStorage = memory();
});

function document(kind) {
  return {
    name: 'demo.pdf',
    mime: 'application/pdf',
    size: 12,
    kind,
    data: 'data:application/pdf;base64,JVBERi0=',
  };
}
function need(category = 'development', amount = 1200000, term = 24) {
  return { category, amount, term, purpose: 'Тестовый запрос' };
}

test('two accounts keep applications and company profiles separate', () => {
  login('anna@demo.local', 'demo123');
  const draft = createApplication('anna', need(), 'growth-start');
  assert.equal(getWorkspace('anna').applications.length, 1);
  assert.equal(getWorkspace('maxim').applications.length, 0);
  assert.throws(() => getApplication('maxim', draft.id), /не найдена/);
  const oldName = draft.company.name;
  saveCompany('anna', { ...getWorkspace('anna').company, name: 'ООО «Новая компания»' });
  assert.equal(getApplication('anna', draft.id).company.name, oldName);
});

test('missing document causes request for information; resubmission preserves checks', () => {
  const draft = createApplication('anna', need(), 'growth-start');
  const missing = submitApplication('anna', draft.id);
  assert.equal(missing.status, 'NEEDS_INFO');
  addDocument('anna', draft.id, document('financial'));
  const result = submitApplication('anna', draft.id);
  assert.equal(result.status, 'DECISION_PENDING');
  assert.equal(result.checks.length, 2);
  assert.deepEqual(
    result.history.map((entry) => entry.status),
    [
      'DRAFT',
      'SUBMITTED',
      'CHECKING',
      'NEEDS_INFO',
      'SUBMITTED',
      'CHECKING',
      'SCORING',
      'DECISION_PENDING',
    ],
  );
  assert.equal(getBankApplication('bank', 'anna', draft.id).application.status, 'DECISION_PENDING');
  assert.equal(reviewApplication('bank', 'anna', draft.id, 'approve').status, 'APPROVED');
  acceptOffer('anna', draft.id);
  assert.equal(signDemo('anna', draft.id).status, 'DISBURSED_DEMO');
});

test('simulated bank rejects a risky profile and forbids signing', () => {
  const company = getWorkspace('maxim').company;
  saveCompany('maxim', { ...company, registeredAt: '2022-01-01' });
  const draft = createApplication('maxim', need('turnover', 300000, 12), 'turnover-flex');
  addDocument('maxim', draft.id, document('financial'));
  const result = submitApplication('maxim', draft.id);
  assert.equal(result.status, 'DECISION_PENDING');
  assert.ok(riskReasons(result).length > 0);
  assert.throws(() => reviewApplication('bank', 'maxim', draft.id, 'approve'), /невозможно/);
  assert.throws(() => reviewApplication('bank', 'maxim', draft.id, 'reject'), /причину/);
  const rejected = reviewApplication(
    'bank',
    'maxim',
    draft.id,
    'reject',
    'Высокая долговая нагрузка',
  );
  assert.equal(rejected.status, 'REJECTED');
  assert.deepEqual(rejected.decision.reasons, ['Высокая долговая нагрузка']);
  assert.throws(() => acceptOffer('maxim', draft.id), /переход/);
});

test('catalog has multiple offers in each category with synthetic versions', () => {
  for (const category of ['development', 'turnover', 'overdraft']) {
    assert.ok(products.filter((item) => item.category === category).length >= 2);
  }
  assert.ok(products.every((item) => item.id && item.version && item.rate));
});

test('an ineligible offer still opens a draft that can be corrected before submission', () => {
  const draft = createApplication('maxim', need('turnover', 1200000, 24), 'growth-start');
  assert.equal(draft.status, 'DRAFT');
  assert.equal(draft.need.category, 'development');
  assert.equal(
    evaluateProduct(
      products.find((item) => item.id === draft.productId),
      draft.need,
      draft.company,
    ).fits,
    false,
  );
  assert.throws(() => submitApplication('maxim', draft.id), /не подходит/);
  const updated = saveDraft('maxim', draft.id, {
    need: { amount: 800000, term: 24 },
    company: { registeredAt: '2022-01-01', revenue: 500000 },
  });
  assert.equal(
    evaluateProduct(
      products.find((item) => item.id === draft.productId),
      updated.need,
      updated.company,
    ).fits,
    true,
  );
  addDocument('maxim', draft.id, document('financial'));
  assert.equal(submitApplication('maxim', draft.id).status, 'DECISION_PENDING');
  assert.equal(
    reviewApplication('bank', 'maxim', draft.id, 'reject', 'Деморешение сотрудника').status,
    'REJECTED',
  );
});

test('employee sees both clients but cannot use client operations or review a draft', () => {
  const anna = createApplication('anna', need(), 'growth-start');
  const maxim = createApplication('maxim', need('turnover', 300000, 12), 'turnover-flex');
  assert.equal(getBankApplications('bank').length, 0);
  assert.throws(() => getBankApplication('bank', 'anna', anna.id), /Черновик/);
  submitApplication('anna', anna.id);
  submitApplication('maxim', maxim.id);
  assert.equal(getBankApplications('bank').length, 2);
  assert.throws(() => getBankApplications('anna'), /недоступен/);
  assert.throws(() => getWorkspace('bank'), /недоступен/);
  login('bank@demo.local', 'demo123');
  assert.equal(getSession(), 'bank');
});

test('employee requests information; client resubmits and receives a decision', () => {
  const draft = createApplication('anna', need(), 'growth-start');
  addDocument('anna', draft.id, document('financial'));
  submitApplication('anna', draft.id);
  assert.throws(() => reviewApplication('bank', 'anna', draft.id, 'request_info'), /сведения/);
  assert.equal(
    reviewApplication('bank', 'anna', draft.id, 'request_info', 'Уточните выручку').status,
    'NEEDS_INFO',
  );
  saveDraft('anna', draft.id, { company: { revenue: 1500000 } });
  assert.equal(submitApplication('anna', draft.id).status, 'DECISION_PENDING');
  assert.equal(
    reviewApplication('bank', 'anna', draft.id, 'approve', 'Проверка пройдена').status,
    'APPROVED',
  );
  assert.equal(getApplication('anna', draft.id).decision.note, 'Проверка пройдена');
  assert.throws(
    () => reviewApplication('bank', 'anna', draft.id, 'reject', 'Повтор'),
    /не ожидает/,
  );
});

test('employee can create a reviewable demo application from an empty queue', () => {
  assert.throws(() => createDemoReviewApplication('anna'), /недоступен/);
  const application = createDemoReviewApplication('bank');
  assert.equal(application.status, 'DECISION_PENDING');
  assert.equal(getBankApplications('bank').length, 1);
  assert.equal(getWorkspace('anna').applications[0].id, application.id);
  assert.equal(reviewApplication('bank', 'anna', application.id, 'approve').status, 'APPROVED');
});
