type ErrorStateProps = {
  message: string;
  onRetry: () => void;
};

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-box error-state" role="alert">
      <div>
        <strong>Không thể tải dữ liệu thời tiết</strong>
        <p>{message}</p>
      </div>
      <button className="pill-button selected" type="button" onClick={onRetry}>
        Thử lại
      </button>
    </div>
  );
}
