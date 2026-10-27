/** Marcador de mapa com um coração: "o lugar certo" + "doação". Mesmo desenho de app/icon.svg. */
export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="8" fill="#1F5F5B" />
      <path
        d="M16 26s-8-7.2-8-13a8 8 0 0 1 16 0c0 5.8-8 13-8 13Z"
        fill="none"
        stroke="#FAF7F2"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <path
        d="M16 17.2s-3.4-2.3-3.4-4.5a1.9 1.9 0 0 1 3.4-1.1 1.9 1.9 0 0 1 3.4 1.1c0 2.2-3.4 4.5-3.4 4.5Z"
        fill="#C2603A"
      />
    </svg>
  );
}
