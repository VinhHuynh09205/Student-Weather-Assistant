import { useState, useEffect, useRef } from "react";

/**
 * Custom hook to detect scroll direction and determine if the bottom navigation
 * bar should be hidden (scrolling down) or visible (scrolling up / near top).
 * Only activates for mobile viewports (max-width: 768px).
 *
 * @param threshold The scroll distance in pixels to trigger visibility toggle.
 */
export function useAutoHideBottomNav(threshold = 10) {
  const [isHidden, setIsHidden] = useState(false);
  const lastScrollY = useRef(0);
  const [isMobile, setIsMobile] = useState(() => 
    typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches
  );
  const [isInputFocused, setIsInputFocused] = useState(false);

  // Monitor media query to dynamically enable/disable the auto-hide behavior
  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(max-width: 768px)");
    const handleMediaQueryChange = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) {
        setIsHidden(false);
      }
    };

    // Modern API support
    mediaQuery.addEventListener("change", handleMediaQueryChange);
    return () => {
      mediaQuery.removeEventListener("change", handleMediaQueryChange);
    };
  }, []);

  // Monitor focus inside inputs/textareas to prevent keyboard overlap issues
  useEffect(() => {
    if (typeof document === "undefined") return;

    const handleFocusIn = (e: FocusEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        setIsInputFocused(true);
      }
    };

    const handleFocusOut = (e: FocusEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        // Small delay in case focus shifts to another input quickly
        setTimeout(() => {
          const activeTag = document.activeElement?.tagName;
          if (activeTag !== "INPUT" && activeTag !== "TEXTAREA") {
            setIsInputFocused(false);
          }
        }, 100);
      }
    };

    document.addEventListener("focusin", handleFocusIn);
    document.addEventListener("focusout", handleFocusOut);

    return () => {
      document.removeEventListener("focusin", handleFocusIn);
      document.removeEventListener("focusout", handleFocusOut);
    };
  }, []);

  // Monitor window scroll events
  useEffect(() => {
    if (!isMobile) {
      setIsHidden(false);
      return;
    }

    if (isInputFocused) {
      // Always hide bottom nav when keyboard/input is focused
      setIsHidden(true);
      return;
    }

    let ticking = false;

    const updateScrollDirection = () => {
      const currentScrollY = window.scrollY;

      // Always show near the top of the page (below 40px)
      if (currentScrollY < 40) {
        setIsHidden(false);
        lastScrollY.current = currentScrollY;
        ticking = false;
        return;
      }

      const diff = currentScrollY - lastScrollY.current;

      if (Math.abs(diff) > threshold) {
        if (diff > 0) {
          // Scrolling down -> Hide
          setIsHidden(true);
        } else {
          // Scrolling up -> Show
          setIsHidden(false);
        }
        lastScrollY.current = currentScrollY;
      }
      ticking = false;
    };

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(updateScrollDirection);
        ticking = true;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, [isMobile, isInputFocused, threshold]);

  return isHidden;
}
