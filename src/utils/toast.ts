export type AppToastVariant = "success" | "error" | "info" | "warning";

export type AppToastPayload = {
  title: string;
  message: string;
  variant?: AppToastVariant;
};

export const appToastEventName = "student-weather:toast";

export function showAppToast(payload: AppToastPayload): void {
  window.dispatchEvent(
    new CustomEvent<AppToastPayload>(appToastEventName, {
      detail: payload,
    }),
  );
}

export function showSuccessToast(title: string, message: string): void {
  showAppToast({ title, message, variant: "success" });
}

export function showErrorToast(title: string, message: string): void {
  showAppToast({ title, message, variant: "error" });
}
