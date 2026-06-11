import { useState } from "react";
import { X, Lock, User as UserIcon, LogIn, UserPlus } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const [isLoginTab, setIsLoginTab] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSyncPrompt, setShowSyncPrompt] = useState(false);

  const { login, register, loginGoogle, syncLocalData } = useAuth();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Basic regex validation for username
    if (!/^[a-zA-Z0-9_.]+$/.test(username)) {
      setError("Tên đăng nhập chỉ gồm chữ cái, số, dấu gạch dưới (_) và dấu chấm (.)");
      return;
    }
    if (username.length < 3 || username.length > 30) {
      setError("Tên đăng nhập phải dài từ 3 đến 30 ký tự.");
      return;
    }

    setIsSubmitting(true);

    try {
      if (isLoginTab) {
        await login(username, password);
      } else {
        if (password !== confirmPassword) {
          setError("Mật khẩu xác nhận không khớp.");
          setIsSubmitting(false);
          return;
        }
        if (password.length < 8) {
          setError("Mật khẩu phải chứa ít nhất 8 ký tự.");
          setIsSubmitting(false);
          return;
        }
        await register(username, password, confirmPassword, fullName);
      }

      // Check if we need to sync local data
      const localLoc = localStorage.getItem("student_weather_confirmed_location");
      const localSched = localStorage.getItem("student_weather_study_schedule");
      if (localLoc || localSched) {
        setShowSyncPrompt(true);
      } else {
        onClose();
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Đã xảy ra lỗi, vui lòng thử lại.";
      setError(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSyncConfirm = async (confirm: boolean) => {
    if (confirm) {
      try {
        await syncLocalData();
      } catch (e) {
        console.error("Failed to sync:", e);
      }
    }
    setShowSyncPrompt(false);
    onClose();
  };

  const handleGoogleSuccessMock = async () => {
    // Generate a mock or direct id_token for demonstration
    // Since Google Identity Services runs on frontend, we mock the success token
    setError("");
    setIsSubmitting(true);
    try {
      // Direct post mock id token to verify OAuth login
      const mockToken = "mock_google_id_token";
      await loginGoogle(mockToken);
      
      const localLoc = localStorage.getItem("student_weather_confirmed_location");
      const localSched = localStorage.getItem("student_weather_study_schedule");
      if (localLoc || localSched) {
        setShowSyncPrompt(true);
      } else {
        onClose();
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Đăng nhập Google thất bại.";
      setError(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-modal-overlay">
      <div className="auth-modal-container glass-effect">
        <button type="button" className="auth-modal-close" onClick={onClose} aria-label="Close">
          <X size={20} />
        </button>

        {showSyncPrompt ? (
          <div className="sync-prompt-content">
            <h2 className="modal-title">Đồng bộ dữ liệu</h2>
            <p className="modal-description">
              Chúng tôi phát hiện bạn có lịch học hoặc vị trí đã lưu trên trình duyệt này. Bạn có muốn đồng bộ các dữ liệu này vào tài khoản để dùng trên các thiết bị khác không?
            </p>
            <div className="sync-buttons-row">
              <button
                type="button"
                className="btn-primary"
                onClick={() => handleSyncConfirm(true)}
              >
                Đồng ý đồng bộ
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleSyncConfirm(false)}
              >
                Bỏ qua
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="auth-tabs-row">
              <button
                type="button"
                className={`auth-tab-btn ${isLoginTab ? "active" : ""}`}
                onClick={() => {
                  setIsLoginTab(true);
                  setError("");
                }}
              >
                <LogIn size={16} />
                Đăng nhập
              </button>
              <button
                type="button"
                className={`auth-tab-btn ${!isLoginTab ? "active" : ""}`}
                onClick={() => {
                  setIsLoginTab(false);
                  setError("");
                }}
              >
                <UserPlus size={16} />
                Đăng ký
              </button>
            </div>

            <h2 className="modal-title">
              {isLoginTab ? "Chào mừng trở lại!" : "Tạo tài khoản mới"}
            </h2>
            <p className="modal-description">
              {isLoginTab
                ? "Đăng nhập để đồng bộ lịch học và vị trí của bạn."
                : "Đăng ký tài khoản để bắt đầu lưu lịch học lâu dài."}
            </p>

            {error && <div className="auth-error-banner">{error}</div>}

            <form onSubmit={handleSubmit} className="auth-form">
              {!isLoginTab && (
                <div className="input-group-with-icon">
                  <UserIcon size={18} className="input-field-icon" />
                  <input
                    type="text"
                    placeholder="Họ và tên"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    className="auth-input-field"
                  />
                </div>
              )}

              <div className="input-group-with-icon">
                <UserIcon size={18} className="input-field-icon" />
                <input
                  type="text"
                  placeholder="Tên đăng nhập"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="auth-input-field"
                />
              </div>

              <div className="input-group-with-icon">
                <Lock size={18} className="input-field-icon" />
                <input
                  type="password"
                  placeholder="Mật khẩu"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="auth-input-field"
                />
              </div>

              {!isLoginTab && (
                <div className="input-group-with-icon">
                  <Lock size={18} className="input-field-icon" />
                  <input
                    type="password"
                    placeholder="Xác nhận mật khẩu"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="auth-input-field"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="auth-submit-btn btn-primary"
              >
                {isSubmitting
                  ? "Vui lòng chờ..."
                  : isLoginTab
                  ? "Đăng nhập"
                  : "Đăng ký tài khoản"}
              </button>
            </form>

            <div className="auth-divider">
              <span>hoặc đăng nhập bằng</span>
            </div>

            <button
              type="button"
              onClick={handleGoogleSuccessMock}
              disabled={isSubmitting}
              className="google-login-btn"
            >
              <svg className="google-icon" viewBox="0 0 24 24">
                <path
                  fill="#EA4335"
                  d="M12 5.04c1.66 0 3.2.57 4.38 1.69l3.27-3.27C17.67 1.54 14.98 1 12 1 7.35 1 3.37 3.65 1.4 7.56l3.87 3C6.2 7.74 8.87 5.04 12 5.04z"
                />
                <path
                  fill="#4285F4"
                  d="M23.49 12.27c0-.82-.07-1.61-.21-2.38H12v4.51h6.48c-.28 1.48-1.12 2.73-2.38 3.58l3.7 2.87c2.16-1.99 3.69-4.92 3.69-8.58z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.27 14.56c-.24-.72-.38-1.5-.38-2.31s.14-1.59.38-2.31l-3.87-3C.5 8.78 0 10.33 0 12s.5 3.22 1.4 4.75l3.87-3.19z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c3.24 0 5.97-1.07 7.96-2.91l-3.7-2.87c-1.03.69-2.35 1.1-4.26 1.1-3.13 0-5.8-2.7-6.73-5.52l-3.87 3C3.37 20.35 7.35 23 12 23z"
                />
              </svg>
              Đăng nhập với Google
            </button>
          </>
        )}
      </div>
    </div>
  );
}
