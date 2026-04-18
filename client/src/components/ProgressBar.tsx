interface Props {
  current: number;
  total: number;
}

const ProgressBar = ({ current, total }: Props) => {
  const pct = Math.min(100, Math.max(0, (current / total) * 100));
  return (
    <div className="w-full">
      <div className="h-1 w-full bg-surface-2">
        <div
          className="h-full bg-foreground transition-[width] duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 flex justify-between text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
        <span>Step {current} of {total}</span>
        <span>{Math.round(pct)}%</span>
      </div>
    </div>
  );
};

export default ProgressBar;
