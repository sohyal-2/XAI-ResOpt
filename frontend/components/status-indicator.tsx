type StatusIndicatorProps = { label: string; status: "ok" | "error" };

export function StatusIndicator({ label, status }: StatusIndicatorProps) {
  const isHealthy = status === "ok";
  return (
    <li className="flex items-center justify-between border-b border-neutral-200 py-3 last:border-b-0">
      <span>{label}</span>
      <span className={isHealthy ? "text-emerald-700" : "text-red-700"}>
        {isHealthy ? "Connected" : "Unavailable"}
      </span>
    </li>
  );
}