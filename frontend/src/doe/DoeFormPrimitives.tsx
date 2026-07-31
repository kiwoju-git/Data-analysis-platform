import { useId, type ReactNode } from "react";

export function DoeFormSection({
  children,
  description,
  title,
}: {
  children: ReactNode;
  description?: string;
  title: string;
}) {
  const headingId = useId();
  return (
    <section className="doe-form-section" aria-labelledby={headingId}>
      <div className="doe-form-section-heading">
        <div>
          <h4 id={headingId}>{title}</h4>
          {description ? <p>{description}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

export function DoeFieldGrid({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`doe-field-grid ${className}`.trim()}>{children}</div>;
}

export function DoeFactorEditor({
  action,
  children,
  description,
  title = "요인 범위",
}: {
  action?: ReactNode;
  children: ReactNode;
  description?: string;
  title?: string;
}) {
  const headingId = useId();
  return (
    <section className="doe-factor-editor" aria-labelledby={headingId}>
      <div className="doe-form-section-heading">
        <div>
          <h4 id={headingId}>{title}</h4>
          {description ? <p>{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function DoeAdvancedSettings({
  children,
  summaryText,
}: {
  children: ReactNode;
  summaryText?: string;
}) {
  return (
    <details className="doe-advanced-settings">
      <summary>
        고급 설정
        {summaryText ? <span>{summaryText}</span> : null}
      </summary>
      <div className="doe-advanced-settings-body">{children}</div>
    </details>
  );
}

export function DoeActionBar({
  children,
  summary,
}: {
  children: ReactNode;
  summary: ReactNode;
}) {
  return (
    <div className="doe-action-bar">
      <div className="doe-validation-summary">{summary}</div>
      <div className="button-row">{children}</div>
    </div>
  );
}
