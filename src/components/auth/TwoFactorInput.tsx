import React, { useState, useRef, useEffect } from "react";
import { ShieldAlert, ArrowLeft, Loader2 } from "lucide-react";

interface TwoFactorInputProps {
  onVerify: (code: string) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
}

export function TwoFactorInput({ onVerify, onCancel, isLoading }: TwoFactorInputProps) {
  const [code, setCode] = useState<string[]>(Array(6).fill(""));
  const [errorMsg, setErrorMsg] = useState("");
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    // Focus the first input box on mount
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, []);

  const handleChange = (index: number, value: string) => {
    // Only accept numeric inputs
    if (value && !/^\d+$/.test(value)) return;

    const newCode = [...code];
    // Keep only the last character entered
    newCode[index] = value.substring(value.length - 1);
    setCode(newCode);
    setErrorMsg("");

    // Move to next input box if value is entered
    if (value && index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto submit if all 6 digits are filled
    const fullCode = newCode.join("");
    if (fullCode.length === 6) {
      handleVerification(fullCode);
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (!code[index] && index > 0 && inputRefs.current[index - 1]) {
        // Move focus to previous input box and clear it
        const newCode = [...code];
        newCode[index - 1] = "";
        setCode(newCode);
        inputRefs.current[index - 1]?.focus();
      } else {
        const newCode = [...code];
        newCode[index] = "";
        setCode(newCode);
      }
      setErrorMsg("");
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim();
    if (!/^\d{6}$/.test(pastedData)) {
      setErrorMsg("Vui lòng dán mã gồm đúng 6 chữ số.");
      return;
    }

    const newCode = pastedData.split("");
    setCode(newCode);
    setErrorMsg("");
    
    // Focus the last input box
    inputRefs.current[5]?.focus();
    
    handleVerification(pastedData);
  };

  const handleVerification = async (otpCode: string) => {
    try {
      await onVerify(otpCode);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Xác thực mã OTP thất bại.");
      // Clear input fields on error and focus first
      setCode(Array(6).fill(""));
      inputRefs.current[0]?.focus();
    }
  };

  return (
    <div className="two-factor-input-container">
      <div className="two-factor-header-icon">
        <ShieldAlert size={36} className="tfa-shield-icon" />
      </div>
      
      <h2 className="two-factor-title">Xác thực 2 yếu tố (2FA)</h2>
      <p className="two-factor-description">
        Tài khoản của bạn đã được kích hoạt bảo mật nâng cao. Vui lòng nhập mã OTP gồm 6 chữ số từ ứng dụng Google Authenticator.
      </p>

      {errorMsg && <div className="auth-error-banner">{errorMsg}</div>}

      <div className="otp-inputs-row">
        {code.map((digit, idx) => (
          <input
            key={idx}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={1}
            value={digit}
            onChange={(e) => handleChange(idx, e.target.value)}
            onKeyDown={(e) => handleKeyDown(idx, e)}
            onPaste={handlePaste}
            disabled={isLoading}
            ref={(el) => { inputRefs.current[idx] = el; }}
            className="otp-digit-input"
            autoComplete="one-time-code"
          />
        ))}
      </div>

      <div className="otp-actions-row">
        <button
          type="button"
          className="btn-back-to-login"
          onClick={onCancel}
          disabled={isLoading}
        >
          <ArrowLeft size={16} /> Quay lại đăng nhập
        </button>

        {isLoading && (
          <span className="otp-loading-indicator">
            <Loader2 size={16} className="animate-spin" /> Đang xác thực...
          </span>
        )}
      </div>
    </div>
  );
}
