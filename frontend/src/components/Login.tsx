import { accounts } from "../mock-api";
import { initials } from "../lib/format";
import { values } from "../app/context";
import { Brand, Eyebrow, Field, Button, Icon } from "./ui";

export function Login({
  onLogin,
}: {
  onLogin: (email: string, password: string) => void;
}) {
  return (
    <div className="login-shell">
      <div className="login-art">
        <div className="login-brand">
          <Brand />
        </div>
        <div className="login-message">
          <div className="login-graphic">
            <span className="graphic-circle c1" />
            <span className="graphic-circle c2" />
            <span className="graphic-arc" />
          </div>
          <span className="overline-light">ФИНАНСИРОВАНИЕ ДЛЯ БИЗНЕСА</span>
          <h1>
            Возможности
            <br />
            начинаются
            <br />
            здесь.
          </h1>
          <p>Один кабинет для выбора кредита, заявки и понятного решения.</p>
        </div>
        <div className="login-art-foot">
          Альфа-Хак 2026 · Демонстрационный прототип
        </div>
      </div>
      <div className="login-panel">
        <div className="login-card">
          <div className="mobile-brand">
            <Brand />
          </div>
          <Eyebrow>КРЕДИТНЫЙ КАБИНЕТ</Eyebrow>
          <h2>Добро пожаловать</h2>
          <p className="muted">Войдите, чтобы продолжить работу с заявками</p>
          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault();
              const data = values(event.currentTarget);
              onLogin(String(data.email), String(data.password));
            }}
          >
            <Field
              name="email"
              label="Электронная почта"
              type="email"
              autoComplete="username"
              placeholder="name@example.com"
              required
            />
            <Field
              name="password"
              label="Пароль"
              type="password"
              autoComplete="current-password"
              placeholder="Введите пароль"
              required
            />
            <Button type="submit" wide>
              Войти в кабинет <Icon name="arrow" size={19} />
            </Button>
          </form>
          <div className="demo-accounts">
            <div className="demo-title">ТЕСТОВЫЕ АККАУНТЫ</div>
            {accounts.map((account, index) => (
              <button
                key={account.id}
                type="button"
                className="demo-account"
                onClick={() => onLogin(account.email, account.password)}
              >
                <span className={`demo-avatar ${index ? "avatar-blue" : ""}`}>
                  {initials(account.name)}
                </span>
                <span>
                  <strong>{account.name}</strong>
                  <small>{account.role === "employee" ? "Сотрудник банка" : "Предприниматель"} · {account.email} · demo123</small>
                </span>
                <Icon name="arrow" size={16} />
              </button>
            ))}
          </div>
          <p className="login-disclaimer">
            <Icon name="info" size={16} /> Это прототип хакатона. Реальные
            банковские операции не выполняются.
          </p>
        </div>
      </div>
    </div>
  );
}
