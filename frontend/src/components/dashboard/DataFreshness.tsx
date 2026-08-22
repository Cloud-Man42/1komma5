import { formatRelativeTime } from "@/lib/format";

export function DataFreshness({
  updatedAt,
  stale,
}: {
  updatedAt: string | null | undefined;
  stale?: boolean;
}) {
  if (!updatedAt) {
    return <span className="data-freshness">Ingen data</span>;
  }
  return (
    <span className="data-freshness">
      Uppdaterad {formatRelativeTime(updatedAt)}
      {stale ? " · inaktuell" : ""}
    </span>
  );
}
