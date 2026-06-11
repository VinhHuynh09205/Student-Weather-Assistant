type LoadingStateProps = {
  message?: string;
};

export function LoadingState({ message = "Đang tải dữ liệu thời tiết..." }: LoadingStateProps) {
  return (
    <div className="state-box" role="status">
      <span className="loading-orb" />
      <span>{message}</span>
    </div>
  );
}
