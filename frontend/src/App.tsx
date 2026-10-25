import * as React from 'react';
import { useEffect, useState } from 'react';
import { api, type BankApplication, type User } from './api';
import type { Application, Company, Need, Product } from './mock-api';
import { AppContext, defaultNeed, readRoute, type AppContextValue } from './app/context';
import { Login } from './components/Login';
import { Header } from './components/Header';
import { Assistant, AssistantContext } from './components/Assistant';
import { Icon } from './components/ui';
import { Home } from './pages/Home';
import { CompanyPage } from './pages/Company';
import { NeedPage } from './pages/Need';
import { CatalogPage } from './pages/Catalog';
import { ApplicationsPage } from './pages/Applications';
import { DetailPage } from './pages/Detail';
import { ResultPage } from './pages/Result';
import { ContractPage } from './pages/Contract';
import { BankDashboard } from './pages/BankDashboard';

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [company, setCompany] = useState<Company | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [bankApplications, setBankApplications] = useState<BankApplication[]>([]);
  const [route, setRoute] = useState(readRoute);
  const [need, setNeed] = useState<Need>(defaultNeed);
  const [selected, setSelected] = useState<string[]>([]);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    error: boolean;
  } | null>(null);
  const refresh = async (account: User | null = user) => {
    if (account?.role === 'employee') {
      setBankApplications(await api.bankApplications());
      return;
    }
    const [nextCompany, nextApplications, nextProducts] = await Promise.all([
      api.company(),
      api.applications(),
      api.products(),
    ]);
    setCompany(nextCompany);
    setApplications(nextApplications);
    setProducts(nextProducts);
  };
  useEffect(() => {
    api
      .me()
      .then(async (current) => {
        await refresh(current);
        setUser(current);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    const handler = () => setRoute(readRoute());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 4500);
    return () => window.clearTimeout(timeout);
  }, [toast]);
  useEffect(() => {
    if (!user) return;
    const update = () => {
      if (document.visibilityState === 'visible') refresh(user).catch(() => {});
    };
    window.addEventListener('focus', update);
    const interval = window.setInterval(update, 15000);
    return () => {
      window.removeEventListener('focus', update);
      window.clearInterval(interval);
    };
  }, [user]);
  const go = (page: string, id?: string) => {
    location.hash = `/${page}${id ? `?id=${encodeURIComponent(id)}` : ''}`;
    setRoute(readRoute());
    window.scrollTo({ top: 0, behavior: 'instant' });
  };
  const notice = (message: string, error = false) => setToast({ message, error });
  const run = async (action: () => Promise<unknown> | void) => {
    try {
      await action();
    } catch (error) {
      notice(error instanceof Error ? error.message : 'Что-то пошло не так.', true);
    }
  };
  const loginUser = (email: string, password: string) =>
    run(async () => {
      const account = await api.login(email, password);
      await refresh(account);
      setUser(account);
      go(account.role === 'employee' ? 'bank' : 'home');
      notice(`Добро пожаловать, ${account.name.split(' ')[0]}!`);
    });
  const logoutUser = () =>
    run(async () => {
      await api.logout();
      setUser(null);
      setCompany(null);
      setApplications([]);
      setProducts([]);
      setBankApplications([]);
      setAssistantOpen(false);
      go('home');
    });
  if (loading) return <div className="error-page">Загружаем кабинет…</div>;
  if (!user)
    return (
      <>
        <Login onLogin={loginUser} />
        {toast && <Toast {...toast} />}
      </>
    );
  if (user.role === 'employee')
    return (
      <>
        <BankDashboard
          user={user}
          applications={bankApplications}
          applicationId={route.page === 'bank' ? route.id : ''}
          go={go}
          run={run}
          refresh={() => refresh(user)}
          notice={notice}
          onLogout={logoutUser}
        />
        {toast && <Toast {...toast} />}
      </>
    );
  const value: AppContextValue = {
    user,
    company,
    applications,
    products,
    route,
    need,
    setNeed,
    selected,
    setSelected,
    go,
    run,
    notice,
    refresh: () => refresh(user),
  };
  let page: React.ReactNode;
  try {
    if (
      ['application', 'result', 'contract'].includes(route.page) &&
      !applications.some((item) => item.id === route.id)
    )
      throw new Error('Заявка не найдена');
    page = (
      {
        home: <Home />,
        company: <CompanyPage />,
        need: <NeedPage />,
        catalog: <CatalogPage />,
        applications: <ApplicationsPage />,
        application: <DetailPage />,
        result: <ResultPage />,
        contract: <ContractPage />,
      } as Record<string, React.ReactNode>
    )[route.page] || <Home />;
  } catch (error) {
    page = (
      <div className="error-page">
        <h2>Не удалось открыть страницу</h2>
        <p>{error instanceof Error ? error.message : 'Неизвестная ошибка'}</p>
        <a className="button button-primary" href="#/applications">
          К списку заявок
        </a>
      </div>
    );
  }
  return (
    <AppContext.Provider value={value}>
      <AssistantContext.Provider value={() => setAssistantOpen((open) => !open)}>
        <Header onLogout={logoutUser}>{page}</Header>
        {assistantOpen && <Assistant close={() => setAssistantOpen(false)} />}
        {toast && <Toast {...toast} />}
      </AssistantContext.Provider>
    </AppContext.Provider>
  );
}
function Toast({ message, error }: { message: string; error: boolean }) {
  return (
    <div className={`toast ${error ? 'toast-error' : ''}`} role="status">
      <Icon name={error ? 'info' : 'check'} size={17} /> {message}
    </div>
  );
}
