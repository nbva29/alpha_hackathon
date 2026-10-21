import * as React from "react";
import { statusNames, type Status } from "../mock-api";
import gridIcon from "../assets/icons/grid.svg";
import buildingIcon from "../assets/icons/building.svg";
import walletIcon from "../assets/icons/wallet.svg";
import fileIcon from "../assets/icons/file.svg";
import arrowIcon from "../assets/icons/arrow.svg";
import backIcon from "../assets/icons/back.svg";
import checkIcon from "../assets/icons/check.svg";
import sparkIcon from "../assets/icons/spark.svg";
import clockIcon from "../assets/icons/clock.svg";
import shieldIcon from "../assets/icons/shield.svg";
import closeIcon from "../assets/icons/close.svg";
import uploadIcon from "../assets/icons/upload.svg";
import chevronIcon from "../assets/icons/chevron.svg";
import exitIcon from "../assets/icons/exit.svg";
import infoIcon from "../assets/icons/info.svg";

const icons = {
  grid: gridIcon,
  building: buildingIcon,
  wallet: walletIcon,
  file: fileIcon,
  arrow: arrowIcon,
  back: backIcon,
  check: checkIcon,
  spark: sparkIcon,
  clock: clockIcon,
  shield: shieldIcon,
  close: closeIcon,
  upload: uploadIcon,
  chevron: chevronIcon,
  exit: exitIcon,
  info: infoIcon,
} as const;
export type IconName = keyof typeof icons;
export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  const src = icons[name];
  return (
    <span
      className="icon-image"
      style={{ width: size, height: size, maskImage: `url("${src}")`, WebkitMaskImage: `url("${src}")` }}
      aria-hidden="true"
    >
      <img src={src} width={size} height={size} alt="" />
    </span>
  );
}
export function Brand() {
  return (
    <>
      <span className="brand-mark">А</span>
      <span>
        АЛЬФА<span className="brand-dot">.</span>ХАК
      </span>
    </>
  );
}
export function Button({
  children,
  variant = "primary",
  wide = false,
  small = false,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "white";
  wide?: boolean;
  small?: boolean;
}) {
  return (
    <button
      className={`button button-${variant}${wide ? " button-wide" : ""}${small ? " button-sm" : ""} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
export function Field({
  label,
  name,
  value,
  type = "text",
  ...props
}: {
  label: string;
  name: string;
  value?: string | number;
  type?: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        key={`${name}-${value}`}
        name={name}
        type={type}
        defaultValue={value ?? ""}
        {...props}
      />
    </label>
  );
}
export function SelectField({
  label,
  name,
  value,
  options,
}: {
  label: string;
  name: string;
  value: string | number;
  options: [string, string][];
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select name={name} defaultValue={String(value)}>
        {options.map(([key, title]) => (
          <option key={key} value={key}>
            {title}
          </option>
        ))}
      </select>
    </label>
  );
}
export function Eyebrow({ children }: { children: React.ReactNode }) {
  return <div className="eyebrow">{children}</div>;
}
export function Intro({
  tag,
  title,
  subtitle,
  side,
}: {
  tag: string;
  title: string;
  subtitle: string;
  side?: React.ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        <Eyebrow>{tag}</Eyebrow>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {side}
    </div>
  );
}
export function StatusPill({ status }: { status: Status }) {
  return (
    <span className={`status status-${status.toLowerCase()}`}>
      <span className="status-dot" />
      {statusNames[status]}
    </span>
  );
}
export function PanelHeading({
  icon,
  title,
  subtitle,
}: {
  icon: IconName;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="panel-heading">
      <span className="panel-icon">
        <Icon name={icon} size={23} />
      </span>
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}
export function Empty({
  title,
  message,
  label,
  onClick,
}: {
  title: string;
  message: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon name="file" size={26} />
      </div>
      <h3>{title}</h3>
      <p>{message}</p>
      <Button onClick={onClick}>{label}</Button>
    </div>
  );
}
