import { ArrowLeft, CalendarDays, GraduationCap } from "lucide-react";
import { Card } from "../common/Card";

export function StudyEmptyState() {
  return (
    <Card className="study-empty-state-card glass-card">
      <div className="empty-state-content">
        <div className="empty-state-icon">
          <GraduationCap size={48} className="cap-icon" />
          <CalendarDays size={32} className="calendar-icon" />
        </div>
        <h3>Lên kế hoạch đi học an toàn</h3>
        <p>
          Thiết lập thời gian học và phương tiện di chuyển ở bảng điều khiển bên trái, sau đó bấm <strong>Lưu lịch học</strong> để nhận điểm số an toàn đi học, cảnh báo thời tiết chi tiết, lộ trình di chuyển và danh sách đồ dùng chuẩn bị.
        </p>
        <div className="empty-state-guide">
          <ArrowLeft size={18} className="guide-arrow" />
          <span>Bắt đầu nhập lịch học của bạn ở cột bên trái</span>
        </div>
      </div>
    </Card>
  );
}
