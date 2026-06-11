import { useEffect, useState } from "react";
import { getNowForTimezone } from "../utils/timeHelpers";

export function useRealtimeClock(timezone?: string): Date {
  const [now, setNow] = useState(() => getNowForTimezone(timezone));

  useEffect(() => {
    setNow(getNowForTimezone(timezone));

    const intervalId = setInterval(() => {
      setNow(getNowForTimezone(timezone));
    }, 1000);

    return () => clearInterval(intervalId);
  }, [timezone]);

  return now;
}
