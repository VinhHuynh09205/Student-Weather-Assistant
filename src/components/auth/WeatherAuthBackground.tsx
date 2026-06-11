import React, { useEffect, useState } from "react";

export function WeatherAuthBackground() {
  const [weatherType, setWeatherType] = useState<"clear-day" | "rainy-day" | "night">(() => {
    const hour = new Date().getHours();
    if (hour >= 6 && hour < 18) {
      // Default to clear day, but make a 40% chance of rain for variety
      return Math.random() < 0.4 ? "rainy-day" : "clear-day";
    }
    return "night";
  });

  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mediaQuery.matches);

    const listener = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  const changeWeather = (type: "clear-day" | "rainy-day" | "night") => {
    setWeatherType(type);
  };

  const particles = Array.from({ length: reducedMotion ? 5 : 25 }, (_, i) => i);
  const clouds = Array.from({ length: 3 }, (_, i) => i);

  return (
    <div className={`auth-bg-stage theme-${weatherType} ${reducedMotion ? "reduced-motion" : ""}`}>
      {/* Sky Gradients */}
      <div className="auth-sky-gradient" />

      {/* Sun or Moon */}
      {weatherType !== "night" ? (
        <div className="auth-sun-disc" />
      ) : (
        <div className="auth-moon-disc">
          <span />
          <span />
        </div>
      )}

      {/* Slowly Drifting Clouds */}
      <div className="auth-cloud-layer">
        {clouds.map((cloud) => (
          <div key={cloud} className={`auth-cloud auth-cloud-${cloud}`} />
        ))}
      </div>

      {/* Weather Particles */}
      <div className="auth-particle-layer">
        {weatherType === "rainy-day" &&
          particles.map((p) => (
            <span
              key={p}
              className="auth-rain-drop"
              style={{
                left: `${(p * 4) % 100}%`,
                animationDelay: `${(p * 0.15) % 3}s`,
                animationDuration: `${1 + (p % 2) * 0.5}s`,
              }}
            />
          ))}

        {weatherType === "clear-day" &&
          particles.map((p) => (
            <span
              key={p}
              className="auth-sun-ray"
              style={{
                left: `${(p * 5) % 100}%`,
                top: `${(p * 3) % 100}%`,
                transform: `scale(${0.5 + (p % 3) * 0.25})`,
                animationDelay: `${(p * 0.2) % 4}s`,
                animationDuration: `${3 + (p % 3)}s`,
              }}
            />
          ))}

        {weatherType === "night" &&
          particles.map((p) => (
            <span
              key={p}
              className="auth-star"
              style={{
                left: `${(p * 7) % 95 + 2}%`,
                top: `${(p * 11) % 90 + 5}%`,
                animationDelay: `${(p * 0.3) % 3}s`,
                animationDuration: `${1.5 + (p % 2) * 0.8}s`,
              }}
            />
          ))}
      </div>

      {/* Glow Effects */}
      <div className="auth-ambient-glow" />

      {/* Weather switcher controls in corner for interactive delight */}
      <div className="auth-weather-switcher" aria-label="Thay đổi thời tiết nền">
        <button
          type="button"
          className={weatherType === "clear-day" ? "active" : ""}
          onClick={() => changeWeather("clear-day")}
          title="Nắng đẹp"
        >
          ☀️
        </button>
        <button
          type="button"
          className={weatherType === "rainy-day" ? "active" : ""}
          onClick={() => changeWeather("rainy-day")}
          title="Mưa rơi"
        >
          🌧️
        </button>
        <button
          type="button"
          className={weatherType === "night" ? "active" : ""}
          onClick={() => changeWeather("night")}
          title="Đêm sao"
        >
          🌙
        </button>
      </div>
    </div>
  );
}
