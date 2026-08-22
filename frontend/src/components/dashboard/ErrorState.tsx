export function ErrorState({ title, text }: { title: string; text?: string }) {
  return (
    <div className="error-state" role="alert">
      <p className="error-state-title">{title}</p>
      {text && <p className="error-state-text">{text}</p>}
    </div>
  );
}
