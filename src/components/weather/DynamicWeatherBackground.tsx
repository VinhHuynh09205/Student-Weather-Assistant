import type { CSSProperties, PropsWithChildren } from "react";

import type { WeatherTheme } from "../../utils/weatherTheme";

type DynamicWeatherBackgroundProps = PropsWithChildren<{
  theme: WeatherTheme;
}>;

export function DynamicWeatherBackground({ children, theme }: DynamicWeatherBackgroundProps) {
  const rainDrops = Array.from({ length: 28 }, (_, index) => index);
  const stars = Array.from({ length: 34 }, (_, index) => index);
  const windLines = Array.from({ length: 10 }, (_, index) => index);
  const showSun = theme.key === "day" || theme.key === "hot";
  const showMoon = theme.key === "night" || theme.key === "rain-night" || theme.key === "storm-night" || theme.key === "wind-night";

  return (
    <div className={`weather-stage theme-${theme.key} ${theme.isWindy ? "is-windy" : ""}`}>
      <div className="sky-gradient" />
      {showSun && <div className="sun-disc" />}
      {showMoon && (
        <div className="moon-disc">
          <span />
          <span />
        </div>
      )}
      <div className="cloud cloud-a" />
      <div className="cloud cloud-b" />
      <div className="cloud cloud-c" />
      {showMoon && (
        <div className="star-field">
          {stars.map((star) => (
            <span key={star} style={{ "--i": star } as CSSProperties} />
          ))}
        </div>
      )}
      <div className="rain-layer">
        {rainDrops.map((drop) => (
          <span key={drop} style={{ "--i": drop } as CSSProperties} />
        ))}
      </div>
      <div className="wind-layer">
        {windLines.map((line) => (
          <span key={line} style={{ "--i": line } as CSSProperties} />
        ))}
      </div>
      <div className="lightning" />
      <div className="content-layer">{children}</div>
    </div>
  );
}
