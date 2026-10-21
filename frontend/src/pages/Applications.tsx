import { useApp, useWorkspace } from "../app/context";
import { Button, Empty, Icon, Intro } from "../components/ui";
import { ApplicationList } from "../components/ApplicationList";

export function ApplicationsPage() {
  const { go } = useApp();
  const applications = useWorkspace().applications;
  return (
    <>
      <Intro
        tag="ИСТОРИЯ ФИНАНСИРОВАНИЯ"
        title="Мои заявки"
        subtitle="Отслеживайте каждый шаг — от черновика до решения."
        side={
          <Button onClick={() => go("need")}>
            Новая заявка <Icon name="arrow" size={17} />
          </Button>
        }
      />
      <div className="section-head">
        <div>
          <h2>Все заявки</h2>
          <p>Всего: {applications.length}</p>
        </div>
      </div>
      {applications.length ? (
        <ApplicationList applications={applications} />
      ) : (
        <Empty
          title="Заявок пока нет"
          message="Подберите кредит и сохраните первую заявку."
          label="Подобрать кредит"
          onClick={() => go("need")}
        />
      )}
    </>
  );
}
