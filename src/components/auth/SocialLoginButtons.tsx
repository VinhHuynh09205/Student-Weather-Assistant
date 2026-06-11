/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useState } from "react";

interface SocialLoginButtonsProps {
  onGoogleClick: (idToken: string) => Promise<void>;
  disabled: boolean;
}

export function SocialLoginButtons({ onGoogleClick, disabled }: SocialLoginButtonsProps) {
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  const isGoogleConfigured = !!googleClientId && googleClientId !== "your_google_client_id" && !googleClientId.includes("placeholder");

  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);
  const [showFallback, setShowFallback] = useState(false);
  const [sdkError, setSdkError] = useState<string | null>(null);

  // Load Google Identity Services SDK
  useEffect(() => {
    if (!isGoogleConfigured) return;

    // Check if the current context is secure (required by Google GIS library)
    const isSecure = window.location.protocol === "https:" || 
                     window.location.hostname === "localhost" || 
                     window.location.hostname === "127.0.0.1";
    
    if (!isSecure) {
      setSdkError("Google Login yêu cầu kết nối HTTPS bảo mật để hoạt động.");
      setShowFallback(true);
      return;
    }

    if ((window as any).google) {
      setIsGoogleLoaded(true);
      return;
    }

    // Set a timeout of 4.5 seconds. If Google library fails to load or is blocked (e.g. by content blockers),
    // we show the fallback button rather than a blank empty container.
    const timer = setTimeout(() => {
      if (!(window as any).google) {
        setSdkError("Thư viện Google Sign-in bị chặn hoặc không thể tải (kiểm tra chặn quảng cáo/Webview).");
        setShowFallback(true);
      }
    }, 4500);

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      clearTimeout(timer);
      setIsGoogleLoaded(true);
    };
    script.onerror = () => {
      clearTimeout(timer);
      setSdkError("Lỗi mạng khi tải thư viện Google Sign-in.");
      setShowFallback(true);
    };
    document.body.appendChild(script);

    return () => {
      clearTimeout(timer);
    };
  }, [isGoogleConfigured]);

  const [buttonWidth, setButtonWidth] = useState(() => 
    typeof window !== "undefined" && window.innerWidth < 400 ? 270 : 320
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleResize = () => {
      setButtonWidth(window.innerWidth < 400 ? 270 : 320);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Render Google Sign-In Button once loaded
  useEffect(() => {
    if (isGoogleLoaded && isGoogleConfigured && !showFallback && (window as any).google) {
      try {
        const google = (window as any).google;
        google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (response: any) => {
            if (response.credential) {
              onGoogleClick(response.credential);
            }
          },
        });
        
        // Clear previous button render if any to prevent duplicates on resize
        const container = document.getElementById("google-signin-btn-container");
        if (container) {
          container.innerHTML = "";
        }

        google.accounts.id.renderButton(
          container,
          {
            theme: "outline",
            size: "large",
            width: buttonWidth,
            text: "signin_with",
            shape: "pill",
          }
        );
      } catch (e) {
        console.error("Error rendering Google button:", e);
        setSdkError("Lỗi khi dựng nút Google Sign-in.");
        setShowFallback(true);
      }
    }
  }, [isGoogleLoaded, isGoogleConfigured, showFallback, googleClientId, buttonWidth, onGoogleClick]);

  const handleFallbackClick = () => {
    if (sdkError) {
      alert(
        `Không thể đăng nhập bằng Google:\n- ${sdkError}\n\nGợi ý:\n1. Sử dụng kết nối bảo mật HTTPS.\n2. Nếu đang mở trong in-app Webview (Facebook, Zalo, Telegram), hãy nhấp vào menu dấu 3 chấm góc trên bên phải và chọn "Mở bằng trình duyệt" (Safari/Chrome).\n3. Đăng ký/đăng nhập bằng tài khoản và mật khẩu thông thường.`
      );
    } else {
      alert(
        "Chưa cấu hình Google Login.\nVui lòng cung cấp VITE_GOOGLE_CLIENT_ID trong file .env ở frontend và GOOGLE_CLIENT_ID ở backend."
      );
    }
  };

  return (
    <div className="social-auth-buttons-grid" style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
      {/* Google Sign-In Container */}
      <div className="google-signin-wrapper" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
        {isGoogleConfigured && !showFallback ? (
          <div id="google-signin-btn-container" style={{ width: "100%", minHeight: "40px", display: "flex", justifyContent: "center", alignItems: "center" }}>
            {!isGoogleLoaded && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "rgba(255, 255, 255, 0.6)", fontSize: "0.85rem" }}>
                <span className="spinner-mini" style={{ width: "14px", height: "14px" }} />
                <span>Đang tải Google Sign-In...</span>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={handleFallbackClick}
            disabled={disabled}
            className="google-login-btn"
            aria-label="Tiếp tục với Google"
            style={{ width: "100%", maxWidth: buttonWidth ? `${buttonWidth}px` : "320px" }}
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
            <span>{sdkError ? "Đăng nhập bằng Google (Lỗi kết nối)" : "Đăng nhập bằng Google"}</span>
          </button>
        )}
      </div>
    </div>
  );
}
