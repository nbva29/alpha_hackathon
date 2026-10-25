import * as React from 'react';
import { initials } from '../lib/format';
import { useApp } from '../app/context';
import { Brand, Icon, type IconName } from './ui';
import { AssistantToggle } from './Assistant';

const navItems: { page: string; label: string; icon: IconName }[] = [
  { page: 'home', label: 'Главная', icon: 'grid' },
  { page: 'company', label: 'Моя компания', icon: 'building' },
  { page: 'need', label: 'Подобрать кредит', icon: 'wallet' },
  { page: 'applications', label: 'Мои заявки', icon: 'file' },
];
export function Header({
  children,
  onLogout,
}: {
  children: React.ReactNode;
  onLogout: () => void;
}) {
  const { user: account, route } = useApp();
  const current = ['application', 'result', 'contract'].includes(route.page)
    ? 'applications'
    : route.page === 'catalog'
      ? 'need'
      : route.page;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Brand />
        </div>
        <div className="sidebar-group-label">РАБОЧЕЕ ПРОСТРАНСТВО</div>
        <nav aria-label="Основная навигация">
          {navItems.map((item) => (
            <a
              key={item.page}
              href={`#/${item.page}`}
              className={`nav-link ${current === item.page ? 'active' : ''}`}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {current === item.page && <i />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <div className="sidebar-help-icon">
              <Icon name="spark" />
            </div>
            <strong>Нужна подсказка?</strong>
            <p>Мы поможем разобраться с этапами заявки.</p>
            <AssistantToggle />
          </div>
          <div className="sidebar-account">
            <span className="user-avatar">{initials(account.name)}</span>
            <span>
              <strong>{account.name}</strong>
              <small>Предприниматель</small>
            </span>
            <button className="icon-button" type="button" onClick={onLogout} aria-label="Выйти">
              <Icon name="exit" size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-area">
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
