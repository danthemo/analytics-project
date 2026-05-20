import type { AnalysisStatus } from "../types/domain";


type StatusBadgeProps = {
  status: AnalysisStatus;
};


const statusLabels: Record<AnalysisStatus, string> = {
  pending: "Ожидает",
  in_progress: "В обработке",
  completed: "Завершен",
  failed: "Ошибка",
};


export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      {statusLabels[status]}
    </span>
  );
}
