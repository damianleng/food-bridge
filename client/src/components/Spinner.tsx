interface Props {
  message?: string;
}

const Spinner = ({ message }: Props) => (
  <div className="flex flex-col items-center justify-center gap-4 py-16">
    <div className="fb-spinner" aria-label="Loading" />
    {message && <p className="text-sm text-muted-foreground">{message}</p>}
  </div>
);

export default Spinner;
