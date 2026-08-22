export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className={`skeleton skeleton-line ${index === 0 ? "skeleton-line-lg" : ""}`.trim()}
        />
      ))}
    </div>
  );
}
