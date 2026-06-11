import type { StudentAdviceResponse } from "../../types/weather";
import { formatPercent, formatTemperature } from "../../utils/formatters";
import { Card } from "../common/Card";

type StudyTimelineCardProps = {
  advice: StudentAdviceResponse | null;
};

export function StudyTimelineCard({ advice }: StudyTimelineCardProps) {
  const timeline = advice?.timeline;

  return (
    <Card className="study-timeline-card" title="Thời tiết buổi học">
      {timeline ? (
        <div className="study-timeline">
          <TimelineItem
            eyebrow="Trước giờ học"
            label={timeline.before_class.time}
            message={timeline.before_class.message}
            meta={`${timeline.before_class.weather_description}, ${formatTemperature(
              timeline.before_class.temperature_c,
            )}, mưa ${formatPercent(timeline.before_class.precipitation_probability_percent)}`}
          />
          <TimelineItem
            eyebrow="Trong giờ học"
            label={timeline.during_class.time_range}
            message={timeline.during_class.message}
            meta={`Nhiệt độ cao nhất ${formatTemperature(
              timeline.during_class.max_temperature_c,
            )}, mưa cao nhất ${formatPercent(timeline.during_class.max_precipitation_probability_percent)}`}
          />
          <TimelineItem
            eyebrow="Lúc tan học"
            label={timeline.after_class.time}
            message={timeline.after_class.message}
            meta={`${timeline.after_class.weather_description}, ${formatTemperature(
              timeline.after_class.temperature_c,
            )}, mưa ${formatPercent(timeline.after_class.precipitation_probability_percent)}`}
          />
        </div>
      ) : (
        <p className="empty-copy">Đang phân tích thời tiết theo lịch học của bạn.</p>
      )}
    </Card>
  );
}

function TimelineItem({
  eyebrow,
  label,
  message,
  meta,
}: {
  eyebrow: string;
  label: string;
  message: string;
  meta: string;
}) {
  return (
    <article>
      <div>
        <span>{eyebrow}</span>
        <strong>{label}</strong>
      </div>
      <p>{message}</p>
      <small>{meta}</small>
    </article>
  );
}
