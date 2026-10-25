import test from 'node:test';
import assert from 'node:assert/strict';
import { api, setCsrfToken } from './api.ts';

test('login stores CSRF token for subsequent mutations', async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init: init || {} });
    if (String(url).endsWith('/auth/login'))
      return Response.json({
        user: { id: 'anna', name: 'Анна', email: 'anna@demo.local', role: 'entrepreneur' },
        csrfToken: 'test-csrf',
      });
    return Response.json([]);
  };
  try {
    await api.login('anna@demo.local', 'demo123');
    await api.applications();
    await api.recommendations({
      purpose: 'Оборудование',
      category: 'development',
      amount: 1200000,
      term: 24,
    });
    assert.equal(new Headers(calls[0].init.headers).get('X-CSRF-Token'), null);
    assert.equal(new Headers(calls[1].init.headers).get('X-CSRF-Token'), null);
    assert.equal(new Headers(calls[2].init.headers).get('X-CSRF-Token'), 'test-csrf');
    assert.equal(calls[2].init.credentials, 'include');
  } finally {
    globalThis.fetch = original;
    setCsrfToken('');
  }
});

test('company payload matches backend snake_case schema', async () => {
  const original = globalThis.fetch;
  let payload: Record<string, unknown> = {};
  globalThis.fetch = async (_url, init) => {
    payload = JSON.parse(String(init?.body));
    return Response.json({});
  };
  try {
    await api.saveCompany({
      name: 'ООО Тест',
      inn: '1234567890',
      legalForm: 'ООО',
      registeredAt: '2020-01-01',
      industry: 'IT',
      revenue: 1000000,
      expenses: 200000,
      obligations: 10000,
      overdue: false,
    });
    assert.equal(payload.legal_form, 'ООО');
    assert.equal(payload.registered_at, '2020-01-01');
    assert.equal('legalForm' in payload, false);
  } finally {
    globalThis.fetch = original;
  }
});

test('document upload uses multipart without forcing JSON content type', async () => {
  const original = globalThis.fetch;
  let init: RequestInit | undefined;
  globalThis.fetch = async (_url, options) => {
    init = options;
    return Response.json({});
  };
  try {
    await api.uploadDocument(
      'app-1',
      'financial',
      new File(['demo'], 'demo.pdf', { type: 'application/pdf' }),
    );
    assert.ok(init?.body instanceof FormData);
    assert.equal(new Headers(init?.headers).get('Content-Type'), null);
  } finally {
    globalThis.fetch = original;
  }
});

test('application lifecycle calls the backend endpoints with the expected payloads', async () => {
  const original = globalThis.fetch;
  const calls: { url: string; method: string; body?: string }[] = [];
  globalThis.fetch = async (url, init) => {
    calls.push({
      url: String(url),
      method: init?.method || 'GET',
      body: typeof init?.body === 'string' ? init.body : undefined,
    });
    return Response.json({ id: 'app-1' });
  };
  const need = {
    purpose: 'Закупка оборудования',
    category: 'development' as const,
    amount: 1200000,
    term: 24,
  };
  const company = {
    name: 'ООО Тест',
    inn: '1234567890',
    legalForm: 'ООО',
    registeredAt: '2020-01-01',
    industry: 'IT',
    revenue: 1000000,
    expenses: 200000,
    obligations: 10000,
    overdue: false,
  };
  try {
    await api.createApplication(need, 'growth-start');
    await api.saveDraft('app-1', need, company);
    await api.submit('app-1');
    await api.acceptOffer('app-1');
    await api.signDemo('app-1');
    await api.assistant('Что нужно для кредита?', 'app-1');
    assert.deepEqual(
      calls.map(({ url, method }) => `${method} ${url}`),
      [
        'POST /api/applications',
        'PATCH /api/applications/app-1',
        'POST /api/applications/app-1/submit',
        'POST /api/applications/app-1/accept-offer',
        'POST /api/applications/app-1/sign-demo',
        'POST /api/assistant',
      ],
    );
    assert.equal(JSON.parse(calls[0].body || '{}').product_id, 'growth-start');
    assert.equal(JSON.parse(calls[5].body || '{}').application_id, 'app-1');
  } finally {
    globalThis.fetch = original;
  }
});

test('employee queue and decision use dedicated bank endpoints', async () => {
  const original = globalThis.fetch;
  const calls: { url: string; method: string; body?: string }[] = [];
  globalThis.fetch = async (url, init) => {
    calls.push({
      url: String(url),
      method: init?.method || 'GET',
      body: typeof init?.body === 'string' ? init.body : undefined,
    });
    return Response.json([]);
  };
  try {
    await api.bankApplications();
    await api.bankDecision('AH-123', 'request_info', 'Нужна выписка');
    assert.equal(calls[0].url, '/api/bank/applications');
    assert.equal(calls[1].url, '/api/bank/applications/AH-123/decision');
    assert.deepEqual(JSON.parse(calls[1].body || '{}'), {
      action: 'request_info',
      comment: 'Нужна выписка',
    });
    assert.equal(
      api.bankDocumentUrl('AH-123', 'doc-1'),
      '/api/bank/applications/AH-123/documents/doc-1',
    );
  } finally {
    globalThis.fetch = original;
  }
});

test('assistant sends page, comparison and need context with its question', async () => {
  const original = globalThis.fetch;
  let payload: Record<string, unknown> = {};
  globalThis.fetch = async (_url, init) => {
    payload = JSON.parse(String(init?.body));
    return Response.json({ answer: 'Готово', mode: 'local-llm', sources: [] });
  };
  try {
    await api.assistant('Сравни варианты', undefined, {
      page: 'catalog',
      selected_product_ids: ['growth-start', 'growth-plus'],
      need: { purpose: 'Оборудование', category: 'development', amount: 1200000, term: 24 },
    }, [{ role: 'user', text: 'Нужен кредит' }, { role: 'assistant', text: 'Уточните сумму.' }]);
    assert.equal(payload.message, 'Сравни варианты');
    assert.deepEqual(payload.page_context, {
      page: 'catalog',
      selected_product_ids: ['growth-start', 'growth-plus'],
      need: { purpose: 'Оборудование', category: 'development', amount: 1200000, term: 24 },
    });
    assert.deepEqual(payload.history, [
      { role: 'user', text: 'Нужен кредит' },
      { role: 'assistant', text: 'Уточните сумму.' },
    ]);
  } finally {
    globalThis.fetch = original;
  }
});
