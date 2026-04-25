"use client";

import { InputHTMLAttributes, MouseEvent, useEffect, useRef, useState } from "react";

type PasswordInputProps = InputHTMLAttributes<HTMLInputElement>;

export default function PasswordInput({
  className = "",
  onBlur,
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function clearHideTimer() {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }

  function hidePassword() {
    clearHideTimer();
    setVisible(false);
  }

  function showPassword() {
    clearHideTimer();
    setVisible(true);
    timeoutRef.current = setTimeout(() => {
      setVisible(false);
      timeoutRef.current = null;
    }, 5000);
  }

  function toggleVisibility() {
    if (visible) {
      hidePassword();
      return;
    }
    showPassword();
  }

  function handleBlur(event: React.FocusEvent<HTMLInputElement>) {
    hidePassword();
    onBlur?.(event);
  }

  function handleMouseDown(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
  }

  useEffect(() => {
    return () => {
      clearHideTimer();
    };
  }, []);

  return (
    <div className="relative mt-2 w-full">
      <input
        {...props}
        type={visible ? "text" : "password"}
        onBlur={handleBlur}
        className={`${className} block w-full pr-20`}
      />
      <button
        type="button"
        onMouseDown={handleMouseDown}
        onClick={toggleVisibility}
        aria-label={visible ? "Hide password" : "Show password"}
        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs font-semibold text-[#7b5d2c] transition hover:bg-[#f3e4c6] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8a6a34]"
      >
        {visible ? "Hide" : "Show"}
      </button>
    </div>
  );
}
