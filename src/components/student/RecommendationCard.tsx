import { Info } from "lucide-react";

import type { StudentAdviceResponse } from "../../types/weather";
import { Card } from "../common/Card";

type RecommendationCardProps = {
  advice: StudentAdviceResponse | null;
};

export function RecommendationCard({ advice }: RecommendationCardProps) {
  const recommendations =
    advice?.recommendations.length ? advice.recommendations : ["Thời tiết khá ổn, bạn có thể đi học bình thường."];

  return (
    <Card className="recommendation-card" title="Danh sách chuẩn bị">
      <div className="recommendation-list">
        {recommendations.map((recommendation) => (
          <article key={recommendation}>
            <span aria-hidden="true">{resolveRecommendationIcon(recommendation)}</span>
            <p>{recommendation}</p>
            <Info size={18} />
          </article>
        ))}
      </div>
    </Card>
  );
}

function resolveRecommendationIcon(text: string): string {
  const normalized = text.toLowerCase();
  if (normalized.includes("mưa") || normalized.includes("dù")) return "☔";
  if (normalized.includes("nước")) return "💧";
  if (normalized.includes("áo khoác") || normalized.includes("nón") || normalized.includes("nắng")) return "🧥";
  if (normalized.includes("sớm") || normalized.includes("xe")) return "🏍️";
  return "✅";
}
