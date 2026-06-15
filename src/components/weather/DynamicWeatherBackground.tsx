import type { CSSProperties, PropsWithChildren } from "react";

import type { WeatherTheme } from "../../utils/weatherTheme";

type DynamicWeatherBackgroundProps = PropsWithChildren<{
  theme: WeatherTheme;
}>;

export function DynamicWeatherBackground({ children, theme }: DynamicWeatherBackgroundProps) {
  const showSun = theme.key === "day" || theme.key === "hot";
  const showMoon = theme.key === "night" || theme.key === "rain-night" || theme.key === "storm-night" || theme.key === "wind-night";

  return (
    <div className={`weather-stage theme-${theme.key} ${theme.isWindy ? "is-windy" : ""}`}>
      <div className="sky-gradient" />
      <div className="ambient-glow-layer">
        <span className="ambient-glow glow-a" />
        <span className="ambient-glow glow-b" />
        <span className="ambient-glow glow-c" />
      </div>
      <div className="atmosphere-layer">
        <span className="atmosphere-haze haze-a" />
        <span className="atmosphere-haze haze-b" />
      </div>
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
      <div className="horizon-layer">
        <span className="horizon-ridge ridge-a" />
        <span className="horizon-ridge ridge-b" />
        <span className="horizon-water" />
        <span className="horizon-bank" />
        <span className="horizon-reed reed-a" />
        <span className="horizon-reed reed-b" />
      </div>
      {showMoon && (
        <div className="star-field">
          {stars.map((star) => (
            <span key={star.key} style={star.style} />
          ))}
        </div>
      )}
      <div className="rain-layer">
        {rainDrops.map((drop) => (
          <span key={drop.key} style={drop.style} />
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

const rainDrops = Array.from({ length: 34 }, (_, index) => {
  const x = 4 + ((index * 23 + (index % 5) * 7) % 94);
  const drift = index % 2 === 0 ? "-7vw" : "-3vw";

  return {
    key: index,
    style: {
      "--rain-x": `${x}%`,
      "--rain-delay": `${index * -0.075}s`,
      "--rain-duration": `${0.95 + (index % 5) * 0.1}s`,
      "--rain-length": `${5.2 + (index % 4) * 0.8}rem`,
      "--rain-opacity": `${0.42 + (index % 4) * 0.12}`,
      "--rain-drift": drift,
      "--rain-slant": `${10 + (index % 3) * 2}deg`,
    } as CSSProperties,
  };
});

const stars = Array.from({ length: 34 }, (_, index) => ({
  key: index,
  style: {
    "--star-x": `${3 + ((index * 37 + (index % 4) * 11) % 94)}%`,
    "--star-y": `${4 + ((index * 19 + (index % 5) * 13) % 88)}%`,
    "--star-delay": `${index * -0.13}s`,
  } as CSSProperties,
}));

const windLines = Array.from({ length: 10 }, (_, index) => index);
