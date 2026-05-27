export function StatusTag({ value }: { value: string }) {
  return <span className={`tag ${value}`}>{value}</span>;
}
