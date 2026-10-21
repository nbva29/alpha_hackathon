import { getAccount } from "../mock-api";
import { day } from "../lib/format";
import { useApp, useWorkspace } from "../app/context";
import { Button, Empty, Icon, Intro, type IconName } from "../components/ui";
import { ApplicationList } from "../components/ApplicationList";

export function Home() {
  const { userId, go } = useApp();
  const { company, applications } = useWorkspace();
  const firstName = getAccount(userId).name.split(" ")[0];
  const active = applications.filter(
    (item) => !["DISBURSED_DEMO", "REJECTED"].includes(item.status),
  );
  const approved = applications.filter((item) =>
    ["APPROVED", "OFFER_ACCEPTED", "SIGNED_DEMO", "DISBURSED_DEMO"].includes(
      item.status,
    ),
  );
  return (
    <>
      <Intro
        tag="ВАШ БИЗНЕС · ВАШИ ВОЗМОЖНОСТИ"
        title={`Здравствуйте, ${firstName}!`}
        subtitle="Управляйте финансированием бизнеса в одном месте."
        side={
          <div className="date-chip">
            <Icon name="clock" size={17} /> {day(new Date())}
          </div>
        }
      />
      <section className="hero">
        <div className="hero-text">
          <span className="hero-label">КРЕДИТ ДЛЯ ВАШИХ ПЛАНОВ</span>
          <h2>
            Идеи растут.
            <br />
            Мы помогаем.
          </h2>
          <p>
            Расскажите о цели — подберём подходящее предложение и проведём по
            каждому шагу.
          </p>
          <Button variant="white" onClick={() => go("need")}>
            Подобрать финансирование <Icon name="arrow" size={19} />
          </Button>
        </div>
        <div className="hero-art">
          <div className="hero-disc disc-one" />
          <div className="hero-disc disc-two" />
          <div className="hero-disc disc-three" />
          <div className="hero-card">
            <span>АЛЬФА · ХАК</span>
            <b>{company?.name || "Ваш бизнес"}</b>
            <small>Демо-кредитный кабинет</small>
          </div>
        </div>
      </section>
      <div className="stat-grid">
        {[
          [
            "file",
            "Всего заявок",
            applications.length,
            "в вашем кабинете",
            "red",
          ],
          [
            "clock",
            "В работе",
            active.length,
            "ожидают ваших действий",
            "amber",
          ],
          [
            "check",
            "Одобрено",
            approved.length,
            "демонстрационных решений",
            "green",
          ],
        ].map(([symbol, label, count, sub, color]) => (
          <div className="stat-card" key={label}>
            <div className={`stat-icon ${color}`}>
              <Icon name={symbol as IconName} size={22} />
            </div>
            <div>
              <span>{label}</span>
              <strong>{count}</strong>
              <small>{sub}</small>
            </div>
          </div>
        ))}
      </div>
      <div className="section-head">
        <div>
          <h2>Ваши заявки</h2>
          <p>Последние изменения и текущие статусы</p>
        </div>
        <a className="inline-link" href="#/applications">
          Все заявки <Icon name="arrow" size={17} />
        </a>
      </div>
      {applications.length ? (
        <ApplicationList applications={applications.slice(0, 3)} />
      ) : (
        <Empty
          title="Пока нет заявок"
          message="Начните с подбора предложения для вашего бизнеса."
          label="Подобрать кредит"
          onClick={() => go("need")}
        />
      )}
      <div className="home-bottom">
        <div className="info-tile">
          <div className="info-tile-icon">
            <Icon name="building" size={22} />
          </div>
          <div>
            <h3>
              {company ? "Профиль компании заполнен" : "Расскажите о компании"}
            </h3>
            <p>
              {company
                ? `${company.name} · ИНН ${company.inn}`
                : "Сохраните данные один раз, чтобы быстрее создавать заявки."}
            </p>
          </div>
          <a href="#/company">
            <Icon name="arrow" size={18} />
          </a>
        </div>
        <div className="info-tile">
          <div className="info-tile-icon">
            <Icon name="shield" size={22} />
          </div>
          <div>
            <h3>Прозрачный процесс</h3>
            <p>Следите за проверкой и решением в истории заявки.</p>
          </div>
          <a href="#/applications">
            <Icon name="arrow" size={18} />
          </a>
        </div>
      </div>
    </>
  );
}
