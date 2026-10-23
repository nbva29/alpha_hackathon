import * as React from 'react';
import { useEffect, useState } from 'react';
import { getSession, getAccount, login, logout, getApplication, type Need } from './mock-api';
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
  const [userId, setUserId] = useState<string | null>(() => getSession());
  const [route, setRoute] = useState(readRoute);
  const [need, setNeed] = useState<Need>(defaultNeed);
  const [selected, setSelected] = useState<string[]>([]);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    error: boolean;
  } | null>(null);
  const [, setRevision] = useState(0);
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
  const go = (page: string, id?: string) => {
    location.hash = `/${page}${id ? `?id=${encodeURIComponent(id)}` : ''}`;
    setRoute(readRoute());
    window.scrollTo({ top: 0, behavior: 'instant' });
  };
  const notice = (message: string, error = false) => setToast({ message, error });
  const refresh = () => setRevision((value) => value + 1);
  const run = (action: () => void) => {
    try {
      action();
    } catch (error) {
      notice(error instanceof Error ? error.message : 'Что-то пошло не так.', true);
    }
  };
  const loginUser = (email: string, password: string) =>
    run(() => {
      const account = login(email, password);
      setUserId(account.id);
      go(account.role === 'employee' ? 'bank' : 'home');
      notice(`Добро пожаловать, ${account.name.split(' ')[0]}!`);
    });
  const logoutUser = () => {
    logout();
    setUserId(null);
    setAssistantOpen(false);
    go('home');
  };
  if (!userId)
    return (
      <>
        <Login onLogin={loginUser} />
        {toast && <Toast {...toast} />}
      </>
    );
  if (getAccount(userId).role === 'employee')
    return (
      <>
        <BankDashboard
          userId={userId}
          applicationId={route.page === 'bank' ? route.id : ''}
          go={go}
          run={run}
          refresh={refresh}
          notice={notice}
          onLogout={logoutUser}
        />
        {toast && <Toast {...toast} />}
      </>
    );
  const value: AppContextValue = {
    userId,
    route,
    need,
    setNeed,
    selected,
    setSelected,
    go,
    run,
    notice,
    refresh,
  };
  let page: React.ReactNode;
  try {
    if (['application', 'result', 'contract'].includes(route.page))
      getApplication(userId, route.id);
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
