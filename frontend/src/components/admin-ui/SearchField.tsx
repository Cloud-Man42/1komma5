export function SearchField({
  value,
  onChange,
  placeholder = "Sök…",
  label = "Sök",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}) {
  return (
    <label className="admin-search-field">
      <span className="admin-field-label">{label}</span>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="admin-input"
      />
    </label>
  );
}
