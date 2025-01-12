import React, { useState } from "react";

export const ModeToggle: React.FC = () => {
  const [darkMode, setDarkMode] = useState(false);

  const toggleMode = () => {
    setDarkMode(!darkMode);
    if (darkMode) {
      document.documentElement.classList.remove("dark");
    } else {
      document.documentElement.classList.add("dark");
    }
  };

  return (
    <button
      onClick={toggleMode}
      className="p-2 rounded-md bg-secondary text-secondary-foreground
        hover:bg-secondary/80 transition-all"
      aria-label="Toggle Dark Mode"
    >
      {darkMode ? (
        <span role="img" aria-label="Light Mode">
          🌞
        </span>
      ) : (
        <span role="img" aria-label="Dark Mode">
          🌜
        </span>
      )}
    </button>
  );
};
