import { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

type BaseProps = {
  label: string;
  hint?: string;
  error?: string | null;
};

export function FormField({
  label,
  hint,
  error,
  children,
}: BaseProps & { children: ReactNode }) {
  return (
    <label className="admin-form-field">
      <span className="admin-field-label">{label}</span>
      {children}
      {hint ? <span className="admin-field-hint muted">{hint}</span> : null}
      {error ? (
        <span className="admin-field-error" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="admin-input" {...props} />;
}

export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className="admin-select" {...props} />;
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className="admin-textarea" {...props} />;
}
