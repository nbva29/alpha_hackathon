import type { Application, Company, Need, Product } from './mock-api';

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface Recommendation {
  product: Product;
  fits: boolean;
  reasons: string[];
}

export interface BankApplication {
  ownerId: string;
  borrowerName: string;
  application: Application;
}

export interface AssistantReply {
  answer: string;
  mode: 'local-llm' | 'verified-comparison' | 'deterministic-fallback';
  sources: { id: string; name: string }[];
  alternatives?: { product: Product; fits: boolean; pros: string[]; cons: string[] }[];
}

export interface AssistantPageContext {
  page: string;
  selected_product_ids: string[];
  need?: Need;
}

export interface AssistantHistoryMessage {
  role: 'user' | 'assistant';
  text: string;
}

let csrfToken = '';

export function setCsrfToken(value: string | null | undefined) {
  csrfToken = value || '';
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set('Content-Type', 'application/json');
  if (init.method && !['GET', 'HEAD'].includes(init.method.toUpperCase()) && csrfToken)
    headers.set('X-CSRF-Token', csrfToken);
  const response = await fetch(`/api${path}`, { ...init, headers, credentials: 'include' });
  if (!response.ok) {
    let detail = `Ошибка сервера (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === 'string') detail = data.detail;
      else if (Array.isArray(data.detail))
        detail = data.detail.map((item: { msg?: string }) => item.msg).join('; ');
    } catch {
      /* non-JSON response */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async me() {
    const user = await request<User & { csrfToken: string }>('/auth/me');
    setCsrfToken(user.csrfToken);
    return user;
  },
  async login(email: string, password: string) {
    const result = await request<{ user: User; csrfToken: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setCsrfToken(result.csrfToken);
    return result.user;
  },
  async logout() {
    await request('/auth/logout', { method: 'POST' });
    setCsrfToken('');
  },
  company: () => request<Company | null>('/companies/me'),
  saveCompany: (company: Company) =>
    request<Company>('/companies/me', {
      method: 'PUT',
      body: JSON.stringify({
        name: company.name,
        inn: company.inn,
        legal_form: company.legalForm,
        registered_at: company.registeredAt,
        industry: company.industry,
        revenue: company.revenue,
        expenses: company.expenses,
        obligations: company.obligations,
        overdue: company.overdue,
      }),
    }),
  products: () => request<Product[]>('/credit-products'),
  recommendations: (need: Need) =>
    request<Recommendation[]>('/credit-products/recommendations', {
      method: 'POST',
      body: JSON.stringify({ need }),
    }),
  applications: () => request<Application[]>('/applications'),
  application: (id: string) => request<Application>(`/applications/${encodeURIComponent(id)}`),
  createApplication: (need: Need, productId: string) =>
    request<Application>('/applications', {
      method: 'POST',
      body: JSON.stringify({ need, product_id: productId }),
    }),
  saveDraft: (id: string, need: Need, company: Company) =>
    request<Application>(`/applications/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ need, company }),
    }),
  uploadDocument: (id: string, kind: string, file: File) => {
    const form = new FormData();
    form.append('kind', kind);
    form.append('file', file);
    return request(`/applications/${encodeURIComponent(id)}/documents`, {
      method: 'POST',
      body: form,
    });
  },
  deleteDocument: (id: string, documentId: string) =>
    request(`/applications/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
    }),
  submit: (id: string) =>
    request<Application>(`/applications/${encodeURIComponent(id)}/submit`, { method: 'POST' }),
  acceptOffer: (id: string) =>
    request<Application>(`/applications/${encodeURIComponent(id)}/accept-offer`, {
      method: 'POST',
    }),
  signDemo: (id: string) =>
    request<Application>(`/applications/${encodeURIComponent(id)}/sign-demo`, { method: 'POST' }),
  assistant: (message: string, applicationId?: string, pageContext?: AssistantPageContext, history?: AssistantHistoryMessage[]) =>
    request<AssistantReply>('/assistant', {
      method: 'POST',
      body: JSON.stringify({ message, application_id: applicationId || null, page_context: pageContext || null, history: history || [] }),
    }),
  bankApplications: () => request<BankApplication[]>('/bank/applications'),
  bankDecision: (id: string, action: 'approve' | 'reject' | 'request_info', comment: string) =>
    request<Application>(`/bank/applications/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      body: JSON.stringify({ action, comment }),
    }),
  bankDocumentUrl: (applicationId: string, documentId: string) =>
    `/api/bank/applications/${encodeURIComponent(applicationId)}/documents/${encodeURIComponent(documentId)}`,
};
