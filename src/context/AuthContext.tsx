import React, { createContext, useContext, useState, useEffect } from "react";
import type {
  User,
  UserSettingsResponse,
  UserLocationResponse,
  StudyScheduleResponse,
  VehicleType,
} from "../types/weather";
import * as userApi from "../api/userApi";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://sw-alb-v7-1940911359.ap-southeast-1.elb.amazonaws.com";

interface AuthContextType {
  currentUser: User | null;
  accessToken: string | null;
  isLoading: boolean;
  
  // Settings
  settings: UserSettingsResponse;
  updateSettings: (newSettings: Partial<UserSettingsResponse>) => Promise<void>;
  
  // Locations
  savedLocations: UserLocationResponse[];
  fetchLocations: () => Promise<void>;
  addLocation: (loc: {
    label: string;
    display_name: string;
    short_display_name?: string | null;
    latitude: number;
    longitude: number;
    source: string;
    administrative_levels?: import("../types/weather").AdministrativeLevels | null;
    is_default?: boolean;
  }) => Promise<void>;
  removeLocation: (id: string) => Promise<void>;
  setDefaultLoc: (id: string) => Promise<void>;
  
  // Schedules
  schedules: StudyScheduleResponse[];
  fetchSchedules: () => Promise<void>;
  upcomingSchedule: StudyScheduleResponse | null;
  fetchUpcoming: () => Promise<void>;
  addSchedule: (sched: {
    title: string;
    study_date?: string | null;
    start_time: string;
    end_time: string;
    vehicle_type: VehicleType;
    location_id?: string | null;
    repeat_type: string;
    repeat_days?: string[] | null;
    note?: string | null;
    is_active?: boolean;
  }) => Promise<void>;
  editSchedule: (id: string, sched: Partial<StudyScheduleResponse>) => Promise<void>;
  removeSchedule: (id: string) => Promise<void>;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, confirmPassword: string, fullName: string) => Promise<void>;
  loginGoogle: (idToken: string) => Promise<void>;
  logout: () => void;
  syncLocalData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const defaultSettings: UserSettingsResponse = {
  id: "",
  user_id: "",
  temperature_unit: "celsius",
  theme_mode: "auto",
  auto_refresh_enabled: true,
  notification_enabled: true,
  default_vehicle_type: "motorbike",
  default_location_id: null,
  created_at: "",
  updated_at: "",
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(
    localStorage.getItem("student_weather_token")
  );
  const [isLoading, setIsLoading] = useState(true);

  // User Data States
  const [settings, setSettings] = useState<UserSettingsResponse>(() => {
    const local = localStorage.getItem("student_weather_settings");
    if (local) {
      try {
        return { ...defaultSettings, ...JSON.parse(local) };
      } catch {
        return defaultSettings;
      }
    }
    return defaultSettings;
  });

  (window as unknown as { __temperature_unit?: string }).__temperature_unit = settings.temperature_unit;

  const [savedLocations, setSavedLocations] = useState<UserLocationResponse[]>(() => {
    const local = localStorage.getItem("student_weather_saved_locations");
    if (local) {
      try {
        return JSON.parse(local);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [schedules, setSchedules] = useState<StudyScheduleResponse[]>(() => {
    const local = localStorage.getItem("student_weather_saved_schedules");
    if (local) {
      try {
        return JSON.parse(local);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [upcomingSchedule, setUpcomingSchedule] = useState<StudyScheduleResponse | null>(() => {
    const local = localStorage.getItem("student_weather_upcoming_schedule");
    if (local) {
      try {
        return JSON.parse(local);
      } catch {
        return null;
      }
    }
    return null;
  });

  // Fetch functions for authenticated user
  const fetchLocations = async () => {
    const token = localStorage.getItem("student_weather_token");
    if (!token) return;
    try {
      const list = await userApi.getUserLocations();
      setSavedLocations(list);
    } catch (e) {
      console.error("Failed to fetch locations:", e);
    }
  };

  const fetchSchedules = async () => {
    const token = localStorage.getItem("student_weather_token");
    if (!token) return;
    try {
      const list = await userApi.getUserSchedules();
      setSchedules(list);
    } catch (e) {
      console.error("Failed to fetch schedules:", e);
    }
  };

  const fetchUpcoming = async () => {
    const token = localStorage.getItem("student_weather_token");
    if (!token) return;
    try {
      const up = await userApi.getUpcomingSchedule();
      setUpcomingSchedule(up);
    } catch (e) {
      console.error("Failed to fetch upcoming schedule:", e);
    }
  };

  const fetchSettings = async () => {
    const token = localStorage.getItem("student_weather_token");
    if (!token) return;
    try {
      const s = await userApi.getUserSettings();
      setSettings(s);
    } catch (e) {
      console.error("Failed to fetch settings:", e);
    }
  };

  const loadAllUserData = async () => {
    // Run concurrently
    await Promise.all([
      fetchSettings(),
      fetchLocations(),
      fetchSchedules(),
      fetchUpcoming(),
    ]);
  };

  const fetchCurrentUser = async (token: string) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (resp.ok) {
        const user = await resp.json();
        setCurrentUser(user);
        await loadAllUserData();
      } else {
        logout();
      }
    } catch {
      logout();
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("student_weather_token");
      if (token) {
        setAccessToken(token);
        await fetchCurrentUser(token);
      }
      setIsLoading(false);
    };
    initAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-refresh token every 30 minutes to keep session alive
  useEffect(() => {
    if (!currentUser || !accessToken) return;

    const refreshToken = async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("student_weather_token")}`,
          },
        });
        if (resp.ok) {
          const data = await resp.json();
          localStorage.setItem("student_weather_token", data.access_token);
          setAccessToken(data.access_token);
        }
      } catch {
        // Silent fail - token refresh is best-effort
      }
    };

    // Refresh every 30 minutes
    const interval = setInterval(refreshToken, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [currentUser, accessToken]);

  const login = async (username: string, password: string) => {
    const resp = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Đăng nhập thất bại.");
    }
    const data = await resp.json();
    localStorage.setItem("student_weather_token", data.access_token);
    setAccessToken(data.access_token);
    await fetchCurrentUser(data.access_token);
  };

  const register = async (username: string, password: string, confirmPassword: string, fullName: string) => {
    const resp = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, confirm_password: confirmPassword, full_name: fullName }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Đăng ký thất bại.");
    }
    await login(username, password);
  };

  const loginGoogle = async (idToken: string) => {
    const resp = await fetch(`${API_BASE_URL}/api/v1/auth/google/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token: idToken, token_type: "bearer" }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Xác thực Google thất bại.");
    }
    const data = await resp.json();
    localStorage.setItem("student_weather_token", data.access_token);
    setAccessToken(data.access_token);
    await fetchCurrentUser(data.access_token);
  };

  const logout = () => {
    localStorage.removeItem("student_weather_token");
    setAccessToken(null);
    setCurrentUser(null);
    
    // Reset to local guest data
    const localSettings = localStorage.getItem("student_weather_settings");
    setSettings(localSettings ? JSON.parse(localSettings) : defaultSettings);
    
    const localLocs = localStorage.getItem("student_weather_saved_locations");
    setSavedLocations(localLocs ? JSON.parse(localLocs) : []);
    
    const localScheds = localStorage.getItem("student_weather_saved_schedules");
    setSchedules(localScheds ? JSON.parse(localScheds) : []);
    
    setUpcomingSchedule(null);
  };

  // Settings Action
  const updateSettings = async (newSettings: Partial<UserSettingsResponse>) => {
    if (currentUser) {
      try {
        const updated = await userApi.updateUserSettings(newSettings);
        setSettings(updated);
      } catch (e) {
        console.error("Failed to update settings:", e);
        throw e;
      }
    } else {
      const nextSettings = { ...settings, ...newSettings };
      setSettings(nextSettings);
      localStorage.setItem("student_weather_settings", JSON.stringify(nextSettings));
    }
  };

  // Locations Actions
  const addLocation = async (loc: {
    label: string;
    display_name: string;
    short_display_name?: string | null;
    latitude: number;
    longitude: number;
    source: string;
    administrative_levels?: import("../types/weather").AdministrativeLevels | null;
    is_default?: boolean;
  }) => {
    if (currentUser) {
      await userApi.createUserLocation(loc);
      await fetchLocations();
    } else {
      const newLoc: UserLocationResponse = {
        id: Math.random().toString(),
        user_id: "",
        label: loc.label,
        display_name: loc.display_name,
        short_display_name: loc.short_display_name ?? null,
        latitude: loc.latitude,
        longitude: loc.longitude,
        source: loc.source,
        administrative_levels: loc.administrative_levels ?? null,
        is_default: loc.is_default ?? false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      
      let nextLocs = [...savedLocations];
      if (loc.is_default) {
        nextLocs = nextLocs.map(l => ({ ...l, is_default: false }));
      }
      nextLocs.push(newLoc);
      setSavedLocations(nextLocs);
      localStorage.setItem("student_weather_saved_locations", JSON.stringify(nextLocs));
    }
  };

  const removeLocation = async (id: string) => {
    if (currentUser) {
      await userApi.deleteUserLocation(id);
      await fetchLocations();
    } else {
      const nextLocs = savedLocations.filter(l => l.id !== id);
      setSavedLocations(nextLocs);
      localStorage.setItem("student_weather_saved_locations", JSON.stringify(nextLocs));
    }
  };

  const setDefaultLoc = async (id: string) => {
    if (currentUser) {
      await userApi.setDefaultLocation(id);
      await fetchLocations();
      await fetchSettings();
    } else {
      const nextLocs = savedLocations.map(l => ({
        ...l,
        is_default: l.id === id,
      }));
      setSavedLocations(nextLocs);
      localStorage.setItem("student_weather_saved_locations", JSON.stringify(nextLocs));
    }
  };

  // Schedules Actions
  const addSchedule = async (sched: {
    title: string;
    study_date?: string | null;
    start_time: string;
    end_time: string;
    vehicle_type: VehicleType;
    location_id?: string | null;
    repeat_type: string;
    repeat_days?: string[] | null;
    note?: string | null;
    is_active?: boolean;
  }) => {
    if (currentUser) {
      await userApi.createStudySchedule(sched);
      await fetchSchedules();
      await fetchUpcoming();
    } else {
      const newSched: StudyScheduleResponse = {
        id: Math.random().toString(),
        user_id: "",
        title: sched.title,
        study_date: sched.study_date ?? null,
        start_time: sched.start_time,
        end_time: sched.end_time,
        vehicle_type: sched.vehicle_type,
        location_id: sched.location_id ?? null,
        repeat_type: sched.repeat_type,
        repeat_days: sched.repeat_days ?? null,
        note: sched.note ?? null,
        is_active: sched.is_active ?? true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      const nextScheds = [...schedules, newSched];
      setSchedules(nextScheds);
      localStorage.setItem("student_weather_saved_schedules", JSON.stringify(nextScheds));
      
      // Update local upcoming schedule
      setUpcomingSchedule(newSched);
      localStorage.setItem("student_weather_upcoming_schedule", JSON.stringify(newSched));
    }
  };

  const editSchedule = async (id: string, sched: Partial<StudyScheduleResponse>) => {
    if (currentUser) {
      await userApi.updateStudySchedule(id, sched);
      await fetchSchedules();
      await fetchUpcoming();
    } else {
      const nextScheds = schedules.map(s => s.id === id ? { ...s, ...sched, updated_at: new Date().toISOString() } : s);
      setSchedules(nextScheds);
      localStorage.setItem("student_weather_saved_schedules", JSON.stringify(nextScheds));
      
      // Update local upcoming if matches
      if (upcomingSchedule?.id === id) {
        const updatedUpcoming = { ...upcomingSchedule, ...sched };
        setUpcomingSchedule(updatedUpcoming);
        localStorage.setItem("student_weather_upcoming_schedule", JSON.stringify(updatedUpcoming));
      }
    }
  };

  const removeSchedule = async (id: string) => {
    if (currentUser) {
      await userApi.deleteStudySchedule(id);
      await fetchSchedules();
      await fetchUpcoming();
    } else {
      const nextScheds = schedules.filter(s => s.id !== id);
      setSchedules(nextScheds);
      localStorage.setItem("student_weather_saved_schedules", JSON.stringify(nextScheds));
      
      if (upcomingSchedule?.id === id) {
        setUpcomingSchedule(null);
        localStorage.removeItem("student_weather_upcoming_schedule");
      }
    }
  };

  const syncLocalData = async () => {
    const token = localStorage.getItem("student_weather_token");
    if (!token) return;

    // Sync Locations
    const storedLocationsLocal = localStorage.getItem("student_weather_saved_locations");
    if (storedLocationsLocal) {
      try {
        const parsed = JSON.parse(storedLocationsLocal) as UserLocationResponse[];
        for (const loc of parsed) {
          await userApi.createUserLocation({
            label: loc.label,
            display_name: loc.display_name,
            short_display_name: loc.short_display_name,
            latitude: loc.latitude,
            longitude: loc.longitude,
            source: loc.source,
            administrative_levels: loc.administrative_levels,
            is_default: loc.is_default,
          });
        }
        localStorage.removeItem("student_weather_saved_locations");
      } catch (e) {
        console.error("Failed to sync local locations:", e);
      }
    } else {
      // Legacy single location sync
      const storedLocation = localStorage.getItem("student_weather_confirmed_location");
      if (storedLocation) {
        try {
          const parsed = JSON.parse(storedLocation);
          await userApi.createUserLocation({
            label: parsed.label || "Vị trí đã xác nhận",
            display_name: parsed.display_name,
            short_display_name: parsed.short_display_name,
            latitude: parsed.latitude,
            longitude: parsed.longitude,
            source: parsed.source || "user_confirmed",
            administrative_levels: parsed.administrative_levels,
            is_default: true,
          });
          localStorage.removeItem("student_weather_confirmed_location");
        } catch (e) {
          console.error("Failed to sync legacy local location:", e);
        }
      }
    }

    // Sync Schedules
    const storedSchedulesLocal = localStorage.getItem("student_weather_saved_schedules");
    if (storedSchedulesLocal) {
      try {
        const parsed = JSON.parse(storedSchedulesLocal) as StudyScheduleResponse[];
        for (const sched of parsed) {
          await userApi.createStudySchedule({
            title: sched.title,
            study_date: sched.study_date,
            start_time: sched.start_time,
            end_time: sched.end_time,
            vehicle_type: sched.vehicle_type,
            repeat_type: sched.repeat_type || "none",
            repeat_days: sched.repeat_days,
            note: sched.note,
            is_active: sched.is_active,
          });
        }
        localStorage.removeItem("student_weather_saved_schedules");
        localStorage.removeItem("student_weather_upcoming_schedule");
      } catch (e) {
        console.error("Failed to sync local schedules:", e);
      }
    } else {
      // Legacy single schedule sync
      const storedSchedule = localStorage.getItem("student_weather_study_schedule");
      if (storedSchedule) {
        try {
          const parsed = JSON.parse(storedSchedule);
          await userApi.createStudySchedule({
            title: parsed.title || "Lịch học đã lưu",
            study_date: parsed.study_date || null,
            start_time: parsed.start_time,
            end_time: parsed.end_time,
            vehicle_type: parsed.vehicle_type || "motorbike",
            repeat_type: parsed.repeat_type || "none",
            repeat_days: parsed.repeat_days || null,
            note: parsed.note || null,
            is_active: true,
          });
          localStorage.removeItem("student_weather_study_schedule");
        } catch (e) {
          console.error("Failed to sync legacy local schedule:", e);
        }
      }
    }

    // Sync Settings
    const storedSettings = localStorage.getItem("student_weather_settings");
    if (storedSettings) {
      try {
        const parsed = JSON.parse(storedSettings);
        await userApi.updateUserSettings(parsed);
        localStorage.removeItem("student_weather_settings");
      } catch (e) {
        console.error("Failed to sync local settings:", e);
      }
    }

    // Reload all synchronized data from server
    await loadAllUserData();
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        accessToken,
        isLoading,
        settings,
        updateSettings,
        savedLocations,
        fetchLocations,
        addLocation,
        removeLocation,
        setDefaultLoc,
        schedules,
        fetchSchedules,
        upcomingSchedule,
        fetchUpcoming,
        addSchedule,
        editSchedule,
        removeSchedule,
        login,
        register,
        loginGoogle,
        logout,
        syncLocalData,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
