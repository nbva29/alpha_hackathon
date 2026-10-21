import * as React from "react";
import { Icon } from "./ui";

export function Wizard({ step }: { step: 1 | 2 | 3 }) {
  return (
    <div className="wizard-steps">
      {(["Потребность", "Предложение", "Заявка"] as const).map(
        (label, index) => (
          <React.Fragment key={label}>
            {index > 0 && <i />}
            <span
              className={
                step === index + 1 ? "current" : step > index + 1 ? "done" : ""
              }
            >
              <b>
                {step > index + 1 ? <Icon name="check" size={14} /> : index + 1}
              </b>{" "}
              {label}
            </span>
          </React.Fragment>
        ),
      )}
    </div>
  );
}
