import { useEffect, useMemo, useState } from "react";
import { Bell } from "lucide-react";
import { LoadingState } from "./components/common/LoadingState";
import { AppLayout } from "./components/layout/AppLayout";
import { LocationSourcePanel } from "./components/location/LocationSourcePanel";
import { LocationConfirmationCard } from "./components/location/LocationConfirmationCard";
import { LocationDebugPanel } from "./components/location/LocationDebugPanel";
import { DynamicWeatherBackground } from "./components/weather/DynamicWeatherBackground";
import { LocationSearchModal } from "./components/location/LocationSearchModal";
import { useCurrentWeather } from "./hooks/useCurrentWeather";
import { useDailyForecast } from "./hooks/useDailyForecast";
import { useHourlyForecast } from "./hooks/useHourlyForecast";
import { useLocationSource } from "./hooks/useLocationSource";
import { useStudyAdvice } from "./hooks/useStudyAdvice";
import { ForecastPage } from "./pages/ForecastPage";
import { HomePage } from "./pages/HomePage";
import { SettingsPage } from "./pages/SettingsPage";
import { StudyAssistantPage } from "./pages/StudyAssistantPage";
import type { AppView, SearchLocationCandidate } from "./types/weather";
import { formatLocationDisplay, formatShortDate } from "./utils/formatters";
import { resolveWeatherTheme } from "./utils/weatherTheme";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AuthPage } from "./components/auth/AuthPage";
import * as userApi from "./api/userApi";


export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const [activeView, setActiveView] = useState<AppView>(() => {
    const path = window.location.pathname;
    if (path === "/login" || path === "/auth" || path === "/register") {
      return "auth";
    }
    if (path === "/forecast") return "forecast";
    if (path === "/study") return "study";
    if (path === "/settings") return "settings";
    return "home";
  });

  const [isLocationSearchOpen, setIsLocationSearchOpen] = useState(false);

  const handleNavigate = (view: AppView) => {
    if (view === "auth") {
      window.history.pushState({}, "", "/login");
    } else if (view === "home") {
      window.history.pushState({}, "", "/");
    } else {
      window.history.pushState({}, "", `/${view}`);
    }
    setActiveView(view);
  };

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path === "/login" || path === "/auth" || path === "/register") {
        setActiveView("auth");
      } else if (path === "/forecast") {
        setActiveView("forecast");
      } else if (path === "/study") {
        setActiveView("study");
      } else if (path === "/settings") {
        setActiveView("settings");
      } else {
        setActiveView("home");
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const { settings, currentUser, updateSettings } = useAuth();

  // Toast notifications state
  const [toasts, setToasts] = useState<Array<{ id: string; title: string; message: string }>>([]);

  const addToast = (title: string, message: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, title, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 6000);
  };

  // Onboarding prompt state
  const [showOnboardingPrompt, setShowOnboardingPrompt] = useState(false);

  useEffect(() => {
    if (currentUser) {
      const promptedKey = `student_weather_notif_prompted_${currentUser.id}`;
      const hasBeenPrompted = localStorage.getItem(promptedKey);
      
      // If user is logged in, has notifications disabled, and has never been prompted
      if (!hasBeenPrompted && settings.notification_enabled === false) {
        const timer = setTimeout(() => {
          setShowOnboardingPrompt(true);
        }, 1500);
        return () => clearTimeout(timer);
      }
    } else {
      setShowOnboardingPrompt(false);
    }
  }, [currentUser, settings.notification_enabled]);

  const handleAcceptOnboarding = async () => {
    if (currentUser) {
      localStorage.setItem(`student_weather_notif_prompted_${currentUser.id}`, "true");
      setShowOnboardingPrompt(false);

      if ("Notification" in window) {
        try {
          const permission = await Notification.requestPermission();
          if (permission === "granted") {
            await updateSettings({ notification_enabled: true });
          } else {
            updateSettings({ notification_enabled: false });
          }
        } catch (err) {
          console.error("Error requesting permission:", err);
          updateSettings({ notification_enabled: false });
        }
      } else {
        updateSettings({ notification_enabled: false });
      }
    }
  };

  const handleDeclineOnboarding = () => {
    if (currentUser) {
      localStorage.setItem(`student_weather_notif_prompted_${currentUser.id}`, "true");
      setShowOnboardingPrompt(false);
      updateSettings({ notification_enabled: false });
    }
  };

  // Poll in-app notifications
  useEffect(() => {
    if (!currentUser || !settings.notification_enabled) return;

    const fetchAndShowNotifications = async () => {
      try {
        const list = await userApi.getUserNotifications();
        // Filters notifications that are sent and either in_app or browser
        const unread = list.filter(n => n.status === "sent" && (n.channel === "in_app" || n.channel === "browser"));
        for (const notif of unread) {
          // Show in-app toast since the tab is open
          addToast(notif.title, notif.message);

          // Show browser notification if channel is browser and permission is granted
          if (notif.channel === "browser" && Notification.permission === "granted") {
            try {
              new Notification(notif.title, {
                body: notif.message,
              });
            } catch (err) {
              console.error("Error displaying browser notification:", err);
            }
          }
          await userApi.markNotificationAsRead(notif.id);
        }
      } catch (err) {
        console.error("Failed to poll notifications:", err);
      }
    };

    fetchAndShowNotifications();
    const timer = setInterval(fetchAndShowNotifications, 20000);
    return () => clearInterval(timer);
  }, [currentUser, settings.notification_enabled]);

  const location = useLocationSource();

  const { locationMode, locationError, confirmLocation } = location;
  const currentWeather = useCurrentWeather(location.source);
  const hourlyForecast = useHourlyForecast(location.source, 24);
  const dailyForecast = useDailyForecast(location.source, 7);
  const studyAdvice = useStudyAdvice(location.source);

  const theme = useMemo(() => {
    const weatherState = { ...currentWeather.weatherForTheme };
    if (settings.theme_mode === "dark") {
      weatherState.is_day = false;
    }
    return resolveWeatherTheme(weatherState);
  }, [currentWeather.weatherForTheme, settings.theme_mode]);

  const [isRefreshing, setIsRefreshing] = useState(false);
  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        currentWeather.refresh(),
        hourlyForecast.refresh(),
        dailyForecast.refresh(),
        studyAdvice.refresh(),
      ]);
    } catch (e) {
      console.error("Failed to refresh some data:", e);
      throw e;
    } finally {
      setIsRefreshing(false);
    }
  };

  // GPS auto-revert / confirm handler
  useEffect(() => {
    const stored = window.localStorage.getItem("student_weather_confirmed_location");
    if (!stored) return;

    if (locationMode === "current") {
      // Revert if geolocating errors out
      if (locationError) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed && typeof parsed.latitude === "number" && typeof parsed.longitude === "number") {
            confirmLocation(
              parsed.display_name,
              parsed.latitude,
              parsed.longitude,
              parsed.short_display_name,
              parsed.administrative_levels
            );
          }
        } catch (e) {
          console.error("Failed to parse stored location:", e);
        }
      }
      // Revert/confirm when weather data is resolved
      else if (currentWeather.data && !currentWeather.loading) {
        if (currentWeather.data.needs_user_confirmation) {
          // GPS is uncertain! Revert to the stored confirmed location without overwriting it.
          try {
            const parsed = JSON.parse(stored);
            if (parsed && typeof parsed.latitude === "number" && typeof parsed.longitude === "number") {
              confirmLocation(
                parsed.display_name,
                parsed.latitude,
                parsed.longitude,
                parsed.short_display_name,
                parsed.administrative_levels
              );
            }
          } catch (e) {
            console.error("Failed to parse stored location:", e);
          }
        } else {
          // GPS is certain! Automatically confirm this new location.
          confirmLocation(
            currentWeather.data.display_name || currentWeather.data.city,
            currentWeather.data.latitude,
            currentWeather.data.longitude,
            currentWeather.data.short_display_name,
            currentWeather.data.administrative_levels
          );
        }
      }
    }
  }, [
    locationMode,
    locationError,
    currentWeather.data,
    currentWeather.loading,
    confirmLocation,
  ]);

  const currentLocationName =
    location.locationMode === "confirmed"
      ? location.city
      : (formatLocationDisplay(currentWeather.data) ||
         (location.locationMode === "current"
           ? "Vị trí hiện tại"
           : location.city));
  const currentTimeZone = currentWeather.data?.timezone;
  const isWeatherLoading = currentWeather.loading || hourlyForecast.loading || dailyForecast.loading;
  const handleRetry = () => window.location.reload();

  if (activeView === "auth") {
    return (
      <AuthPage
        onLoginSuccess={() => handleNavigate("home")}
        onSkip={() => handleNavigate("home")}
      />
    );
  }

  return (
    <DynamicWeatherBackground theme={theme}>
      <LocationSearchModal
        isOpen={isLocationSearchOpen}
        onClose={() => setIsLocationSearchOpen(false)}
        onSelectLocation={(candidate) =>
          location.confirmLocation(
            candidate.display_name,
            candidate.latitude,
            candidate.longitude,
            candidate.short_display_name,
            candidate.administrative_levels
          )
        }
      />
      <AppLayout
        activeView={activeView}
        timeZone={currentTimeZone}
        onNavigate={handleNavigate}
        onOpenLogin={() => handleNavigate("auth")}
      >
        <div className="page-wrap app-page" key={`${settings.temperature_unit}-${settings.theme_mode}`}>
          <PageHeader
            activeView={activeView}
            city={location.city}
            coordinates={location.currentCoordinates}
            disabled={isWeatherLoading}
            isLocating={location.isLocating}
            locationError={location.locationError}
            locationMode={location.locationMode}
            locationName={currentLocationName}
            locationConfidence={currentWeather.data?.location_confidence}
            accuracyMeters={location.currentCoordinates?.accuracy ?? currentWeather.data?.accuracy_meters}
            timeZone={currentTimeZone}
            onSearch={location.searchCity}
            onUseCurrentLocation={location.useCurrentLocation}
            // Confirmed location features
            searchCandidates={location.searchCandidates}
            isSearchingCandidates={location.isSearching}
            searchCandidatesError={location.searchError}
            onSelectCandidate={(candidate) => location.confirmLocation(candidate.display_name, candidate.latitude, candidate.longitude, candidate.short_display_name, candidate.administrative_levels)}
            onClearConfirmed={() => setIsLocationSearchOpen(true)}
          />

          {location.isLocating ? <LoadingState message="Đang lấy vị trí hiện tại..." /> : null}

          <LocationConfirmationCard
            accuracyMeters={location.currentCoordinates?.accuracy ?? currentWeather.data?.accuracy_meters}
            needsConfirmation={
              location.locationMode !== "confirmed" &&
              (location.locationError !== null ||
               (location.currentCoordinates?.accuracy !== undefined && location.currentCoordinates.accuracy > 500) ||
               currentWeather.data?.needs_user_confirmation === true)
            }
            searchCandidates={location.searchCandidates}
            isSearching={location.isSearching}
            searchError={location.searchError}
            onSearch={location.searchCity}
            onConfirmLocation={location.confirmLocation}
            onUseCurrentLocation={location.requestCurrentLocation}
          />

          <LocationDebugPanel
            gpsCoordinates={location.currentCoordinates}
            locationMode={location.locationMode}
            currentWeather={currentWeather.data}
          />

          {activeView === "home" ? (
            <HomePage
              currentWeather={currentWeather.data}
              currentError={currentWeather.error}
              currentLoading={currentWeather.loading}
              dailyItems={dailyForecast.data?.daily ?? []}
              dailyError={dailyForecast.error}
              dailyLoading={dailyForecast.loading}
              hasSavedSchedule={studyAdvice.hasSavedSchedule}
              hourlyItems={hourlyForecast.data?.hourly ?? []}
              hourlyError={hourlyForecast.error}
              hourlyLoading={hourlyForecast.loading}
              locationMode={location.locationMode}
              locationName={currentLocationName}
              coordinates={location.currentCoordinates}
              studyAdvice={studyAdvice.advice}
              studySchedule={studyAdvice.schedule}
              onOpenStudyAssistant={() => setActiveView("study")}
              onRetry={handleRetry}
              onRefresh={handleManualRefresh}
              isRefreshing={isRefreshing}
            />
          ) : null}

          {activeView === "forecast" ? (
            <ForecastPage
              currentWeather={currentWeather.data}
              currentError={currentWeather.error}
              currentLoading={currentWeather.loading}
              dailyItems={dailyForecast.data?.daily ?? []}
              dailyError={dailyForecast.error}
              dailyLoading={dailyForecast.loading}
              hourlyItems={hourlyForecast.data?.hourly ?? []}
              hourlyError={hourlyForecast.error}
              hourlyLoading={hourlyForecast.loading}
              onRetry={handleRetry}
            />
          ) : null}

          {activeView === "study" ? (
            <StudyAssistantPage
              advice={studyAdvice.advice}
              adviceError={studyAdvice.error}
              currentWeather={currentWeather.data}
              dateMode={studyAdvice.studyDateMode}
              endTime={studyAdvice.endTime}
              isLoading={studyAdvice.loading}
              scheduleError={studyAdvice.scheduleError}
              selectedVehicle={studyAdvice.selectedVehicle}
              startTime={studyAdvice.startTime}
              studyDate={studyAdvice.studyDate}
              onDateChange={studyAdvice.changeStudyDate}
              onDateModeChange={studyAdvice.changeStudyDateMode}
              onEndTimeChange={studyAdvice.setEndTime}
              onPreset={studyAdvice.applyStudyPreset}
              onSaveSchedule={studyAdvice.saveSchedule}
              onStartTimeChange={studyAdvice.setStartTime}
              onVehicleChange={studyAdvice.changeVehicle}
              
              title={studyAdvice.title}
              onTitleChange={studyAdvice.setTitle}
              note={studyAdvice.note}
              onNoteChange={studyAdvice.setNote}
              locationId={studyAdvice.locationId}
              onLocationIdChange={studyAdvice.setLocationId}
              selectedScheduleId={studyAdvice.selectedScheduleId}
              onSelectScheduleId={studyAdvice.setSelectedScheduleId}
              editingScheduleId={studyAdvice.editingScheduleId}
              onEditSchedule={studyAdvice.handleEditSchedule}
              onCancelEdit={studyAdvice.cancelEdit}
              onDeleteSchedule={studyAdvice.handleDeleteSchedule}
            />
          ) : null}

          {activeView === "settings" ? (
            <SettingsPage
              currentWeather={currentWeather.data}
              hasSavedSchedule={studyAdvice.hasSavedSchedule}
              onOpenLogin={() => handleNavigate("auth")}
              onOpenStudyAssistant={() => handleNavigate("study")}
            />
          ) : null}
        </div>
      </AppLayout>

      {/* Global In-app Toast Container */}
      <div className="toast-container" style={{
        position: "fixed",
        bottom: "2rem",
        right: "2rem",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        maxWidth: "350px",
        pointerEvents: "none"
      }}>
        {toasts.map(toast => (
          <div key={toast.id} className="glass-card animate-slide-up" style={{
            padding: "1rem",
            background: "rgba(15, 23, 42, 0.85)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            borderRadius: "0.75rem",
            boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.4)",
            color: "#ffffff",
            pointerEvents: "auto"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.25rem" }}>
              <strong style={{ fontSize: "0.85rem", color: "#3b82f6" }}>{toast.title}</strong>
              <button 
                onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
                style={{
                  background: "none",
                  border: "none",
                  color: "rgba(255,255,255,0.4)",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  padding: 0
                }}
              >
                ✕
              </button>
            </div>
            <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.85)", margin: 0, whiteSpace: "pre-line" }}>
              {toast.message}
            </p>
          </div>
        ))}
      </div>

      {/* Onboarding Notification Consent Prompt */}
      {showOnboardingPrompt && (
        <div className="auth-modal-overlay" style={{ zIndex: 9999 }}>
          <div className="auth-modal-container glass-effect" style={{ maxWidth: "420px", padding: "2rem" }}>
            <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
              <div style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                background: "rgba(59, 130, 246, 0.15)",
                color: "#3b82f6",
                marginBottom: "1rem"
              }}>
                <Bell size={24} />
              </div>
              <h2 className="modal-title" style={{ fontSize: "1.25rem", color: "#ffffff", fontWeight: "bold" }}>
                Nhận thông báo thời tiết
              </h2>
              <p className="modal-description" style={{ fontSize: "0.85rem", color: "rgba(255, 255, 255, 0.7)", marginTop: "0.5rem" }}>
                Bạn có muốn nhận thông báo thời tiết cho lịch học sắp tới không? Chúng tôi sẽ gửi cảnh báo và lời khuyên chuẩn bị trước buổi học.
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                type="button"
                className="btn-primary"
                onClick={handleAcceptOnboarding}
                style={{ flex: 1, padding: "0.6rem", fontSize: "0.85rem", borderRadius: "8px", border: "none", cursor: "pointer" }}
              >
                Đồng ý bật
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleDeclineOnboarding}
                style={{ flex: 1, padding: "0.6rem", fontSize: "0.85rem", borderRadius: "8px", border: "none", cursor: "pointer" }}
              >
                Từ chối
              </button>
            </div>
          </div>
        </div>
      )}
    </DynamicWeatherBackground>
  );
}

function PageHeader({
  activeView,
  city,
  coordinates,
  disabled,
  isLocating,
  locationError,
  locationMode,
  locationName,
  locationConfidence,
  accuracyMeters,
  timeZone,
  onSearch,
  onUseCurrentLocation,
  searchCandidates,
  isSearchingCandidates,
  searchCandidatesError,
  onSelectCandidate,
  onClearConfirmed,
}: {
  activeView: AppView;
  city: string;
  coordinates: ReturnType<typeof useLocationSource>["currentCoordinates"];
  disabled: boolean;
  isLocating: boolean;
  locationError: string | null;
  locationMode: ReturnType<typeof useLocationSource>["locationMode"];
  locationName: string;
  locationConfidence?: string;
  accuracyMeters?: number | null;
  timeZone?: string;
  onSearch: (city: string) => void;
  onUseCurrentLocation: () => void;
  searchCandidates?: SearchLocationCandidate[];
  isSearchingCandidates?: boolean;
  searchCandidatesError?: string | null;
  onSelectCandidate?: (candidate: SearchLocationCandidate) => void;
  onClearConfirmed?: () => void;
}) {
  const { currentUser } = useAuth();
  const content = getHeaderContent(activeView, locationName, timeZone, currentUser?.full_name);

  return (
    <header className="hero-header app-header">
      <div>
        <span>{content.kicker}</span>
        <h1>{content.title}</h1>
        <p>{content.description}</p>
      </div>
      <LocationSourcePanel
        city={city}
        coordinates={coordinates}
        disabled={disabled}
        isLocating={isLocating}
        locationError={locationError}
        locationMode={locationMode}
        locationName={locationName}
        locationConfidence={locationConfidence}
        accuracyMeters={accuracyMeters}
        onSearch={onSearch}
        onUseCurrentLocation={onUseCurrentLocation}
        searchCandidates={searchCandidates}
        isSearchingCandidates={isSearchingCandidates}
        searchCandidatesError={searchCandidatesError}
        onSelectCandidate={onSelectCandidate}
        onClearConfirmed={onClearConfirmed}
      />
    </header>
  );
}

function getGreeting(fullName?: string | null): string {
  const name = fullName || "Sinh viên";
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) {
    return `Chào buổi sáng, ${name} ☀️`;
  } else if (hour >= 12 && hour < 18) {
    return `Chào buổi chiều, ${name} 🌤️`;
  } else {
    return `Chào buổi tối, ${name} 🌙`;
  }
}

function getHeaderContent(
  activeView: AppView,
  locationName: string,
  timeZone?: string,
  fullName?: string | null,
): { kicker: string; title: string; description: string } {
  if (activeView === "forecast") {
    return {
      kicker: "Dự báo thời tiết",
      title: "Dự báo hôm nay và nhiều ngày",
      description: `${locationName} · ${formatShortDate(new Date(), timeZone)}`,
    };
  }

  if (activeView === "study") {
    return {
      kicker: "Cá nhân hóa theo lịch học",
      title: "Trợ lý đi học",
      description: "Thiết lập buổi học để nhận điểm thuận lợi, cảnh báo và danh sách chuẩn bị.",
    };
  }

  if (activeView === "settings") {
    return {
      kicker: "Tùy chỉnh trải nghiệm",
      title: "Cài đặt",
      description: "Quản lý vị trí, lịch học đã lưu và thông tin ứng dụng.",
    };
  }

  return {
    kicker: "Thời tiết hiện tại",
    title: fullName ? getGreeting(fullName) : "Thời tiết quanh bạn",
    description: `${locationName} · ${formatShortDate(new Date(), timeZone)}`,
  };
}
