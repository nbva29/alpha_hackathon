import { type Application } from "../mock-api";
import { day, productById, rub } from "../lib/format";
import { Icon, StatusPill } from "./ui";

function ApplicationRow({ application }: { application: Application }) {
  const product = productById(application.productId);
  return (
    <a
      className="application-row"
      href={`#/application?id=${encodeURIComponent(application.id)}`}
    >
      <div className="app-row-icon">
        <Icon name="file" size={22} />
      </div>
      <div className="app-row-main">
        <strong>{product?.name || "Кредитное предложение"}</strong>
        <small>
          № {application.id} · {day(application.createdAt)}
        </small>
      </div>
      <div className="app-row-amount">
        <strong>{rub(application.need.amount)}</strong>
        <small>на {application.need.term} мес.</small>
      </div>
      <StatusPill status={application.status} />
      <span className="app-row-chevron">
        <Icon name="chevron" size={18} />
      </span>
    </a>
  );
}
export function ApplicationList({
  applications,
}: {
  applications: Application[];
}) {
  return (
    <div className="application-list">
      {applications.map((application) => (
        <ApplicationRow key={application.id} application={application} />
      ))}
    </div>
  );
}
