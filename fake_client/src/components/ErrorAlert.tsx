interface Props {
  message: string;
  onDismiss?: () => void;
}

const ErrorAlert = ({ message, onDismiss }: Props) => (
  <div className="border border-foreground bg-surface px-4 py-3 flex items-start justify-between gap-4" role="alert">
    <div className="text-sm">
      <span className="font-semibold mr-2">Error.</span>{message}
    </div>
    {onDismiss && (
      <button onClick={onDismiss} className="text-sm underline underline-offset-2 shrink-0" aria-label="Dismiss">
        Dismiss
      </button>
    )}
  </div>
);

export default ErrorAlert;
