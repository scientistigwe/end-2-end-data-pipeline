import React from "react";

interface PipelineLogoProps {
  className?: string;
}

const PipelineLogo: React.FC<PipelineLogoProps> = ({ className = "" }) => {
  return (
    <div className={`inline-flex ${className}`}>
      <svg
        viewBox="0 0 200 200"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <circle
          cx="100"
          cy="100"
          r="90"
          fill="#f8fafc"
          stroke="#0f172a"
          strokeWidth="4"
        />
        <path
          d="M40 70 C40 70, 160 70, 160 70"
          stroke="#2563eb"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M40 100 C40 100, 120 100, 120 100"
          stroke="#3b82f6"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M40 130 C40 130, 140 130, 140 130"
          stroke="#60a5fa"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <circle cx="60" cy="70" r="8" fill="#1e40af" />
        <circle cx="120" cy="70" r="8" fill="#1e40af" />
        <circle cx="80" cy="100" r="8" fill="#1e40af" />
        <circle cx="100" cy="130" r="8" fill="#1e40af" />
      </svg>
    </div>
  );
};

export default PipelineLogo;
