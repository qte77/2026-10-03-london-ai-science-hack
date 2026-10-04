import { useEffect, useState } from "react";

const LOOKS = [
  ["polymer", "POLYMER"],
  ["console", "CONSOLE"],
  ["lab80", "LAB-80"],
];

function readInitialLook() {
  // index.html's inline script already set this before first paint; mirror
  // it into React state instead of re-deriving it, so there's one source of
  // truth for "what look is active right now".
  return document.documentElement.dataset.look || "polymer";
}

export default function ThemeSwitcher() {
  const [look, setLook] = useState(readInitialLook);

  useEffect(() => {
    document.documentElement.dataset.look = look;
    try {
      localStorage.setItem("qc-look", look);
    } catch {
      // storage may be blocked (private mode); the attribute is still set.
    }
  }, [look]);

  return (
    <div className="segmented" role="group" aria-label="Look">
      {LOOKS.map(([value, label]) => (
        <button
          key={value}
          type="button"
          aria-pressed={look === value}
          onClick={() => setLook(value)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
