// Browser-local stand-in for the backend and bank simulator. No real banking calls.
const STORE_KEY = 'alfa-hack-credit-demo-v1';
const SESSION_KEY = 'alfa-hack-credit-session-v1';

export type Category = 'development' | 'turnover' | 'overdraft';
export type Status = 'DRAFT' | 'SUBMITTED' | 'CHECKING' | 'NEEDS_INFO' | 'SCORING' | 'DECISION_PENDING' | 'APPROVED' | 'REJECTED' | 'OFFER_ACCEPTED' | 'SIGNED_DEMO' | 'DISBURSED_DEMO';
export type DocumentKind = 'financial' | 'statement';
export interface Company { name: string; inn: string; legalForm: string; registeredAt: string; industry: string; revenue: number; expenses: number; obligations: number; overdue: boolean }
export interface Need { purpose: string; category: Category; amount: number; term: number }
export interface Product { id: string; version: string; name: string; category: Category; purpose: string; min: number; max: number; minTerm: number; maxTerm: number; rate: number; minAge: number; minRevenue: number; document: DocumentKind; extras: string; limit: string }
export interface ApplicationDocument { id: string; name: string; mime: string; size: number; kind: DocumentKind; data: string; addedAt: string }
export interface CheckResult { date: string; fns: string; bki: string; financial: string }
export interface Decision { approved: boolean; reasons: string[]; rate: number; payment: number; decidedAt: string; note: string }
export interface HistoryEvent { status: Status; date: string; description: string }
export interface Application { id: string; status: Status; productId: string; productVersion: string; need: Need; company: Company; documents: ApplicationDocument[]; checks: CheckResult[]; decision: Decision | null; createdAt: string; updatedAt: string; history: HistoryEvent[] }
export interface Workspace { company: Company | null; applications: Application[] }
type UserId = 'anna' | 'maxim';
type Store = Record<UserId, Workspace>;

export const accounts: { id: string; name: string; email: string; password: string; role: 'client' | 'employee' }[] = [
  { id: 'anna', name: 'Анна Смирнова', email: 'anna@demo.local', password: 'demo123', role: 'client' },
  { id: 'maxim', name: 'Максим Петров', email: 'maxim@demo.local', password: 'demo123', role: 'client' },
  { id: 'bank', name: 'Мария Орлова', email: 'bank@demo.local', password: 'demo123', role: 'employee' },
];

export const products: Product[] = [
  { id: 'growth-start', version: 'demo-1', name: 'Бизнес-рост', category: 'development', purpose: 'Оборудование, расширение и новые направления', min: 500000, max: 5000000, minTerm: 12, maxTerm: 48, rate: 16.9, minAge: 12, minRevenue: 300000, document: 'financial', extras: 'Аннуитетный платёж, без залога', limit: 'Бизнесу от 12 месяцев' },
  { id: 'growth-plus', version: 'demo-1', name: 'Бизнес-рост Плюс', category: 'development', purpose: 'Крупные инвестиции в развитие', min: 3000000, max: 15000000, minTerm: 24, maxTerm: 60, rate: 15.9, minAge: 24, minRevenue: 1000000, document: 'financial', extras: 'Индивидуальный график, поручительство', limit: 'Бизнесу от 24 месяцев' },
  { id: 'turnover-flex', version: 'demo-1', name: 'Оборотный Флекс', category: 'turnover', purpose: 'Закупки, сезонные расходы и расчёты', min: 200000, max: 3000000, minTerm: 3, maxTerm: 24, rate: 17.4, minAge: 6, minRevenue: 200000, document: 'financial', extras: 'Досрочное погашение без комиссии', limit: 'Бизнесу от 6 месяцев' },
  { id: 'turnover-pro', version: 'demo-1', name: 'Оборотный Про', category: 'turnover', purpose: 'Пополнение оборотных средств', min: 1000000, max: 8000000, minTerm: 6, maxTerm: 36, rate: 16.4, minAge: 12, minRevenue: 700000, document: 'financial', extras: 'Увеличенный лимит, поручительство', limit: 'Бизнесу от 12 месяцев' },
  { id: 'overdraft-daily', version: 'demo-1', name: 'Овердрафт Лайт', category: 'overdraft', purpose: 'Закрыть короткий кассовый разрыв', min: 100000, max: 1500000, minTerm: 1, maxTerm: 12, rate: 19.2, minAge: 6, minRevenue: 200000, document: 'statement', extras: 'Проценты только за дни использования', limit: 'Бизнесу от 6 месяцев' },
  { id: 'overdraft-business', version: 'demo-1', name: 'Овердрафт Бизнес', category: 'overdraft', purpose: 'Резерв на ежедневные платежи', min: 500000, max: 5000000, minTerm: 1, maxTerm: 12, rate: 18.5, minAge: 12, minRevenue: 600000, document: 'statement', extras: 'Возобновляемый лимит', limit: 'Бизнесу от 12 месяцев' },
];

export const categoryNames: Record<Category, string> = { development: 'Развитие бизнеса', turnover: 'Оборотные средства', overdraft: 'Овердрафт' };
export const statusNames: Record<Status, string> = {
  DRAFT: 'Черновик', SUBMITTED: 'Отправлена', CHECKING: 'Проверка данных', NEEDS_INFO: 'Нужны сведения',
  SCORING: 'Оценка риска', DECISION_PENDING: 'Ожидает решения', APPROVED: 'Одобрена',
  REJECTED: 'Отказ', OFFER_ACCEPTED: 'Условия приняты', SIGNED_DEMO: 'Подписана', DISBURSED_DEMO: 'Выдана (демо)',
};

const initialData = (): Store => ({
  anna: {
    company: { name: 'ООО «Северный свет»', inn: '7708123456', legalForm: 'ООО', registeredAt: '2021-04-15', industry: 'Торговля', revenue: 1250000, expenses: 670000, obligations: 140000, overdue: false },
    applications: [],
  },
  maxim: {
    company: { name: 'ИП Петров Максим Сергеевич', inn: '780123456789', legalForm: 'ИП', registeredAt: '2025-11-12', industry: 'Услуги', revenue: 270000, expenses: 210000, obligations: 110000, overdue: true },
    applications: [],
  },
});

function readData(): Store {
  try {
    const value = JSON.parse(localStorage.getItem(STORE_KEY) || 'null') as Store | null;
    if (value?.anna?.applications && value?.maxim?.applications) return value;
  } catch { /* Reset only malformed local demo state. */ }
  const value = initialData();
  localStorage.setItem(STORE_KEY, JSON.stringify(value));
  return value;
}

function writeData(data: Store) { localStorage.setItem(STORE_KEY, JSON.stringify(data)); }
function scoped<T>(userId: string, operation: (workspace: Workspace) => T): T {
  if (!accounts.some(account => account.id === userId && account.role === 'client')) throw new Error('Кабинет клиента недоступен.');
  const data = readData();
  const result = operation(data[userId as UserId]);
  writeData(data);
  return structuredClone(result);
}
function findApplication(user: Workspace, id: string): Application {
  const item = user.applications.find(application => application.id === id);
  if (!item) throw new Error('Заявка не найдена в вашем кабинете.');
  return item;
}
function transition(application: Application, to: Status, description: string) {
  const allowed: Partial<Record<Status, Status[]>> = {
    DRAFT: ['SUBMITTED'], NEEDS_INFO: ['SUBMITTED'], SUBMITTED: ['CHECKING'], CHECKING: ['NEEDS_INFO', 'SCORING'],
    SCORING: ['DECISION_PENDING'], DECISION_PENDING: ['NEEDS_INFO', 'APPROVED', 'REJECTED'], APPROVED: ['OFFER_ACCEPTED'],
    OFFER_ACCEPTED: ['SIGNED_DEMO'], SIGNED_DEMO: ['DISBURSED_DEMO'],
  };
  if (!allowed[application.status]?.includes(to)) throw new Error('Этот переход для заявки сейчас недоступен.');
  application.status = to;
  application.updatedAt = new Date().toISOString();
  application.history.push({ status: to, date: application.updatedAt, description });
}

export function ageMonths(dateString: string) {
  if (!dateString) return 0;
  const then = new Date(dateString);
  if (Number.isNaN(then.getTime())) return 0;
  const now = new Date();
  return Math.max(0, (now.getFullYear() - then.getFullYear()) * 12 + now.getMonth() - then.getMonth() - (now.getDate() < then.getDate() ? 1 : 0));
}

export function evaluateProduct(product: Product, need: Need, company: Company | null) {
  const reasons = [];
  const amount = Number(need.amount);
  const term = Number(need.term);
  if (need.category && product.category !== need.category) reasons.push('другая цель финансирования');
  if (amount < product.min || amount > product.max) reasons.push('сумма вне диапазона');
  if (term < product.minTerm || term > product.maxTerm) reasons.push('срок вне диапазона');
  if (company && ageMonths(company.registeredAt) < product.minAge) reasons.push('недостаточный срок работы бизнеса');
  if (company && Number(company.revenue) < product.minRevenue) reasons.push('выручка ниже требования');
  return { fits: reasons.length === 0, reasons };
}

export function monthlyPayment(amount: number, annualRate: number, months: number) {
  const principal = Number(amount), count = Number(months), monthlyRate = Number(annualRate) / 1200;
  if (!principal || !count || principal < 0 || count < 0) return 0;
  if (!monthlyRate) return principal / count;
  const factor = (1 + monthlyRate) ** count;
  return principal * monthlyRate * factor / (factor - 1);
}

export function getSession() {
  try { return accounts.find(account => account.id === sessionStorage.getItem(SESSION_KEY))?.id || null; }
  catch { return null; }
}
export function login(email: string, password: string) {
  const account = accounts.find(item => item.email.toLowerCase() === String(email).trim().toLowerCase() && item.password === password);
  if (!account) throw new Error('Неверная почта или пароль демо-аккаунта.');
  sessionStorage.setItem(SESSION_KEY, account.id);
  readData();
  return { id: account.id, name: account.name, email: account.email, role: account.role };
}
export function logout() { sessionStorage.removeItem(SESSION_KEY); }
export function getAccount(userId: string) {
  const account = accounts.find(item => item.id === userId);
  if (!account) throw new Error('Сессия не найдена.');
  return { id: account.id, name: account.name, email: account.email, role: account.role };
}
export function getWorkspace(userId: string) { return scoped(userId, user => user); }
export function saveCompany(userId: string, company: Company) {
  if (!company.name?.trim() || !/^\d{10}(\d{2})?$/.test(company.inn || '') || !company.registeredAt) {
    throw new Error('Укажите название, дату регистрации и ИНН из 10 или 12 цифр.');
  }
  return scoped(userId, user => { user.company = { ...company, revenue: Number(company.revenue), expenses: Number(company.expenses), obligations: Number(company.obligations) }; return user.company; });
}
export function createApplication(userId: string, need: Need, productId: string) {
  const product = products.find(item => item.id === productId);
  if (!product) throw new Error('Выберите предложение.');
  if (!need.purpose?.trim() || Number(need.amount) <= 0 || Number(need.term) <= 0) throw new Error('Заполните цель, сумму и срок.');
  return scoped(userId, user => {
    if (!user.company) throw new Error('Сначала заполните профиль компании.');
    const now = new Date().toISOString();
    const application: Application = {
      id: `AH-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 5).toUpperCase()}`,
      status: 'DRAFT', productId, productVersion: product.version, need: { ...need, category: product.category, amount: Number(need.amount), term: Number(need.term) },
      company: structuredClone(user.company), documents: [], checks: [], decision: null,
      createdAt: now, updatedAt: now, history: [{ status: 'DRAFT', date: now, description: 'Черновик создан' }],
    };
    user.applications.unshift(application);
    return application;
  });
}
export function getApplication(userId: string, id: string) { return scoped(userId, user => findApplication(user, id)); }
export function saveDraft(userId: string, id: string, patch: { company?: Partial<Company>; need?: Partial<Need> }) {
  return scoped(userId, user => {
    const application = findApplication(user, id);
    if (!['DRAFT', 'NEEDS_INFO'].includes(application.status)) throw new Error('Редактирование этой заявки недоступно.');
    if (patch.company) application.company = { ...application.company, ...patch.company };
    if (patch.need) application.need = { ...application.need, ...patch.need };
    application.updatedAt = new Date().toISOString();
    return application;
  });
}
export function addDocument(userId: string, id: string, document: Omit<ApplicationDocument, 'id' | 'addedAt'>) {
  return scoped(userId, user => {
    const application = findApplication(user, id);
    if (!['DRAFT', 'NEEDS_INFO'].includes(application.status)) throw new Error('Документы этой заявки уже отправлены.');
    if (!['application/pdf', 'image/png', 'image/jpeg'].includes(document.mime) || document.size > 1024 * 1024) {
      throw new Error('Загрузите PDF, PNG или JPG размером до 1 МБ.');
    }
    application.documents = application.documents.filter(item => item.kind !== document.kind);
    application.documents.push({ ...document, id: crypto.randomUUID(), addedAt: new Date().toISOString() });
    return application;
  });
}
export function removeDocument(userId: string, id: string, documentId: string) {
  return scoped(userId, user => {
    const application = findApplication(user, id);
    if (!['DRAFT', 'NEEDS_INFO'].includes(application.status)) throw new Error('Документы этой заявки уже отправлены.');
    application.documents = application.documents.filter(item => item.id !== documentId);
    return application;
  });
}
export function submitApplication(userId: string, id: string) {
  return scoped(userId, user => {
    const application = findApplication(user, id);
    const product = products.find(item => item.id === application.productId);
    if (!product) throw new Error('Предложение недоступно.');
    if (!application.company.name?.trim() || !/^\d{10}(\d{2})?$/.test(application.company.inn || '')) throw new Error('Проверьте название компании и ИНН.');
    if (!application.need.purpose?.trim() || !Number(application.need.amount) || !Number(application.need.term)) throw new Error('Проверьте цель, сумму и срок.');
    const eligibility = evaluateProduct(product, application.need, application.company);
    if (!eligibility.fits) throw new Error(`Выбранное предложение не подходит: ${eligibility.reasons.join(', ')}.`);
    transition(application, 'SUBMITTED', 'Заявка отправлена на демонстрационную проверку');
    transition(application, 'CHECKING', 'Симулятор проверяет сведения о компании');
    const check = { date: new Date().toISOString(), fns: 'Данные компании синтетические', bki: application.company.overdue ? 'Есть демо-просрочка' : 'Просрочек нет', financial: 'Финансовые показатели рассчитаны по анкете' };
    application.checks.push(check);
    if (!application.documents.some(item => item.kind === product.document)) {
      transition(application, 'NEEDS_INFO', product.document === 'financial' ? 'Приложите финансовую отчётность' : 'Приложите выписку по счёту');
      return application;
    }
    transition(application, 'SCORING', 'Выполнена условная оценка риска');
    transition(application, 'DECISION_PENDING', 'Ожидает решения сотрудника банка');
    return application;
  });
}
export interface BankApplication { ownerId: string; borrowerName: string; application: Application }
function requireEmployee(userId: string) {
  if (!accounts.some(account => account.id === userId && account.role === 'employee')) throw new Error('Кабинет сотрудника недоступен.');
}
export function getBankApplications(userId: string): BankApplication[] {
  requireEmployee(userId);
  const data = readData();
  return structuredClone((Object.keys(data) as UserId[]).flatMap(ownerId => {
    const borrowerName = accounts.find(account => account.id === ownerId)?.name || ownerId;
    return data[ownerId].applications.filter(application => application.status !== 'DRAFT').map(application => ({ ownerId, borrowerName, application }));
  }).sort((a, b) => b.application.updatedAt.localeCompare(a.application.updatedAt)));
}
export function getBankApplication(userId: string, ownerId: string, id: string): BankApplication {
  requireEmployee(userId);
  if (ownerId !== 'anna' && ownerId !== 'maxim') throw new Error('Заявка не найдена.');
  const application = findApplication(readData()[ownerId], id);
  if (application.status === 'DRAFT') throw new Error('Черновик ещё не отправлен в банк.');
  return structuredClone({ ownerId, borrowerName: accounts.find(account => account.id === ownerId)?.name || ownerId, application });
}
export function createDemoReviewApplication(employeeId: string) {
  requireEmployee(employeeId);
  const draft = createApplication('anna', {
    purpose: 'Закупка оборудования', category: 'development', amount: 1200000, term: 24,
  }, 'growth-start');
  addDocument('anna', draft.id, {
    name: 'демо-отчётность.pdf', mime: 'application/pdf', size: 12,
    kind: 'financial', data: 'data:application/pdf;base64,JVBERi0=',
  });
  return submitApplication('anna', draft.id);
}
export function riskReasons(application: Application): string[] {
  const product = products.find(item => item.id === application.productId);
  if (!product) throw new Error('Предложение недоступно.');
  const disposable = Number(application.company.revenue) - Number(application.company.expenses) - Number(application.company.obligations);
  const payment = monthlyPayment(application.need.amount, product.rate, application.need.term);
  const reasons: string[] = [];
  if (application.company.overdue) reasons.push('По демоданным есть просрочка');
  if (disposable < payment * 1.25) reasons.push('Свободного денежного потока недостаточно для платежа');
  return reasons;
}
export function reviewApplication(employeeId: string, ownerId: string, id: string, action: 'approve' | 'reject' | 'request_info', comment = '') {
  requireEmployee(employeeId);
  if (ownerId !== 'anna' && ownerId !== 'maxim') throw new Error('Заявка не найдена.');
  const data = readData();
  const application = findApplication(data[ownerId], id);
  if (application.status !== 'DECISION_PENDING') throw new Error('Заявка сейчас не ожидает решения.');
  const note = comment.trim();
  if (action === 'request_info') {
    if (!note) throw new Error('Укажите, какие сведения нужны клиенту.');
    transition(application, 'NEEDS_INFO', note);
  } else {
    if (action === 'reject' && !note) throw new Error('Укажите причину отказа.');
    const risks = riskReasons(application);
    if (action === 'approve' && risks.length) throw new Error(`Одобрение невозможно: ${risks.join('; ')}.`);
    const product = products.find(item => item.id === application.productId)!;
    application.decision = {
      approved: action === 'approve', reasons: action === 'reject' ? [note] : [], rate: product.rate,
      payment: monthlyPayment(application.need.amount, product.rate, application.need.term),
      decidedAt: new Date().toISOString(), note: note || 'Одобрено сотрудником банка (демо)',
    };
    transition(application, action === 'approve' ? 'APPROVED' : 'REJECTED', action === 'approve' ? (note || 'Одобрено сотрудником банка (демо)') : note);
  }
  writeData(data);
  return structuredClone(application);
}
export function acceptOffer(userId: string, id: string) { return scoped(userId, user => { const item = findApplication(user, id); transition(item, 'OFFER_ACCEPTED', 'Условия демо-договора приняты'); return item; }); }
export function signDemo(userId: string, id: string) { return scoped(userId, user => { const item = findApplication(user, id); transition(item, 'SIGNED_DEMO', 'Демо-договор подписан'); transition(item, 'DISBURSED_DEMO', 'Демонстрационная выдача выполнена'); return item; }); }
