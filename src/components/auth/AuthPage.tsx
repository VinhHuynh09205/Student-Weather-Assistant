import React, { useState, useEffect } from "react";
import { LogIn, UserPlus, ShieldCheck } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { WeatherAuthBackground } from "./WeatherAuthBackground";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";
import { SocialLoginButtons } from "./SocialLoginButtons";

interface AuthPageProps {
  onLoginSuccess: () => void;
  onSkip: () => void;
}

export function AuthPage({ onLoginSuccess, onSkip }: AuthPageProps) {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSyncPrompt, setShowSyncPrompt] = useState(false);

  const { currentUser, login, register, loginGoogle, syncLocalData } = useAuth();

  // Redirect if already logged in on mount
  useEffect(() => {
    if (currentUser) {
      onLoginSuccess();
    }
  }, [currentUser, onLoginSuccess]);

  // Dynamic viewport height calculation to handle mobile URL bar / keyboard overlays
  useEffect(() => {
    const updateAppHeight = () => {
      const height = window.visualViewport ? window.visualViewport.height : window.innerHeight;
      document.documentElement.style.setProperty("--app-height", `${height}px`);
    };

    updateAppHeight();

    window.addEventListener("resize", updateAppHeight);
    window.addEventListener("orientationchange", updateAppHeight);
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", updateAppHeight);
      window.visualViewport.addEventListener("scroll", updateAppHeight);
    }

    return () => {
      window.removeEventListener("resize", updateAppHeight);
      window.removeEventListener("orientationchange", updateAppHeight);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener("resize", updateAppHeight);
        window.visualViewport.removeEventListener("scroll", updateAppHeight);
      }
    };
  }, []);

  const handleLoginSubmit = async (username: string, password: string) => {
    setError("");
    setIsSubmitting(true);
    try {
      await login(username, password);
      checkSyncRequirement();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
      setIsSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (username: string, password: string, fullName: string) => {
    setError("");
    setIsSubmitting(true);
    try {
      await register(username, password, password, fullName);
      checkSyncRequirement();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng ký thất bại.");
      setIsSubmitting(false);
    }
  };

  const handleGoogleLogin = async (idToken: string) => {
    setError("");
    setIsSubmitting(true);
    try {
      await loginGoogle(idToken);
      checkSyncRequirement();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xác thực Google thất bại.");
      setIsSubmitting(false);
    }
  };

  const checkSyncRequirement = () => {
    const localLoc = localStorage.getItem("student_weather_confirmed_location");
    const localSched = localStorage.getItem("student_weather_study_schedule");
    const localLocsList = localStorage.getItem("student_weather_saved_locations");
    const localSchedsList = localStorage.getItem("student_weather_saved_schedules");
    
    if (localLoc || localSched || localLocsList || localSchedsList) {
      setShowSyncPrompt(true);
    } else {
      onLoginSuccess();
    }
  };

  const handleSyncConfirm = async (confirm: boolean) => {
    setIsSubmitting(true);
    if (confirm) {
      try {
        await syncLocalData();
      } catch (e) {
        console.error("Failed to sync:", e);
      }
    }
    setIsSubmitting(false);
    onLoginSuccess();
  };

  return (
    <div className="auth-fullscreen-layout">
      {/* Dynamic weather backdrop */}
      <WeatherAuthBackground />

      <div className="auth-fullscreen-content">
        {/* Skip button in corner */}
        <button type="button" className="auth-skip-corner-btn" onClick={onSkip}>
          Bỏ qua →
        </button>

        <div className="auth-page-grid">
          {/* Left Decorative Section (Desktop only) */}
          <div className="auth-decor-side auth-decor-left">
            <div className="decor-glass-bubble">
              <span className="decor-icon" role="img" aria-label="sun behind cloud">🌤️</span>
              <h3>Bản tin đi học</h3>
              <p>Phân tích thời tiết thực tế để chuẩn bị đi học tốt nhất.</p>
            </div>
            <div className="decor-glass-bubble delay-1">
              <span className="decor-icon" role="img" aria-label="calendar">📅</span>
              <h3>Lịch trình học tập</h3>
              <p>Quản lý lịch học và nhận cảnh báo thời tiết tương ứng.</p>
            </div>
          </div>

          {/* Center Auth Card */}
          <div className="auth-glass-card-wrapper animate-slide-up">
            {showSyncPrompt ? (
              <div className="auth-card-scrollable-body">
                <div className="sync-prompt-inner-card">
                  <div className="sync-icon-glow">
                    <ShieldCheck size={48} />
                  </div>
                  <h2 className="modal-title sync-modal-title">Đồng bộ dữ liệu thời tiết</h2>
                  <p className="modal-description sync-modal-description">
                    Chúng tôi phát hiện bạn đang có lịch học, cài đặt hoặc vị trí đã lưu dưới dạng khách. Bạn có muốn đồng bộ các dữ liệu này vào tài khoản của mình không?
                  </p>
                  <div className="sync-buttons-row">
                    <button
                      type="button"
                      disabled={isSubmitting}
                      className="btn-primary"
                      onClick={() => handleSyncConfirm(true)}
                    >
                      Đồng ý đồng bộ
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      className="btn-secondary"
                      onClick={() => handleSyncConfirm(false)}
                    >
                      Bỏ qua
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="auth-card-inner-flow">
                {/* Header section (fixed in flow) */}
                <div className="auth-card-header-section">
                  {/* Tab Selector */}
                  <div className="auth-card-tabs-row">
                    <button
                      type="button"
                      className={`auth-card-tab-btn ${activeTab === "login" ? "active" : ""}`}
                      onClick={() => {
                        setActiveTab("login");
                        setError("");
                      }}
                    >
                      <LogIn size={16} />
                      Đăng nhập
                    </button>
                    <button
                      type="button"
                      className={`auth-card-tab-btn ${activeTab === "register" ? "active" : ""}`}
                      onClick={() => {
                        setActiveTab("register");
                        setError("");
                      }}
                    >
                      <UserPlus size={16} />
                      Đăng ký
                    </button>
                  </div>

                  {/* Headline */}
                  <div className="auth-card-header">
                    <h1 className="modal-title">
                      {activeTab === "login" ? "Chào mừng trở lại! 👋" : "Đăng ký tài khoản"}
                    </h1>
                    <p className="modal-description">
                      {activeTab === "login"
                        ? "Đăng nhập để xem thời tiết và gợi ý đi học hôm nay"
                        : "Đăng ký tài khoản để bắt đầu lưu lịch học lâu dài"}
                    </p>
                  </div>
                </div>

                {/* Scrollable body section */}
                <div className="auth-card-scrollable-body">
                  {/* Active Tab Form */}
                  {activeTab === "login" ? (
                    <LoginForm
                      onSubmit={handleLoginSubmit}
                      isLoading={isSubmitting}
                      errorMsg={error}
                    />
                  ) : (
                    <RegisterForm
                      onSubmit={handleRegisterSubmit}
                      isLoading={isSubmitting}
                      errorMsg={error}
                    />
                  )}

                  <div className="auth-divider">
                    <span>hoặc tiếp tục với</span>
                  </div>

                  {/* Social Login options */}
                  <SocialLoginButtons
                    onGoogleClick={handleGoogleLogin}
                    disabled={isSubmitting}
                  />

                  <div className="auth-card-footer-cta">
                    {activeTab === "login" ? (
                      <p>
                        Chưa có tài khoản?{" "}
                        <button type="button" onClick={() => setActiveTab("register")}>
                          Đăng ký ngay
                        </button>
                      </p>
                    ) : (
                      <p>
                        Đã có tài khoản?{" "}
                        <button type="button" onClick={() => setActiveTab("login")}>
                          Đăng nhập ngay
                        </button>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Decorative Section (Desktop only) */}
          <div className="auth-decor-side auth-decor-right">
            <div className="decor-glass-bubble delay-2">
              <span className="decor-icon" role="img" aria-label="round pin">📍</span>
              <h3>Lưu trữ vị trí</h3>
              <p>Lưu vị trí nhà riêng, giảng đường hay ký túc xá dễ dàng.</p>
            </div>
            <div className="decor-glass-bubble delay-3">
              <span className="decor-icon" role="img" aria-label="high voltage">⚡</span>
              <h3>Đồng bộ tức thời</h3>
              <p>Trải nghiệm lưu dữ liệu ổn định và phục hồi nhanh chóng.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
