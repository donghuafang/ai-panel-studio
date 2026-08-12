import { MIN_EXPERTS, MAX_EXPERTS } from '../lib/constants';

const DOT_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
];

interface GuestCountSliderProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

export default function GuestCountSlider({
  value,
  onChange,
  disabled = false,
}: GuestCountSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-300">
          专家人数
        </label>
        <span className="text-sm font-semibold text-studio-accent">
          {value} 位专家
        </span>
      </div>

      {/* Slider */}
      <input
        type="range"
        min={MIN_EXPERTS}
        max={MAX_EXPERTS}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        className={`h-2 w-full cursor-pointer appearance-none rounded-full bg-studio-border accent-studio-accent ${
          disabled ? 'cursor-not-allowed opacity-50' : ''
        }`}
      />

      {/* Tick marks */}
      <div className="flex justify-between px-1">
        {Array.from({ length: MAX_EXPERTS - MIN_EXPERTS + 1 }, (_, i) => {
          const n = MIN_EXPERTS + i;
          return (
            <span
              key={n}
              className={`text-xs ${
                n === value ? 'text-studio-accent font-medium' : 'text-gray-500'
              }`}
            >
              {n}
            </span>
          );
        })}
      </div>

      {/* Dot preview */}
      <div className="flex items-center justify-center gap-2 pt-1">
        {Array.from({ length: value }, (_, i) => (
          <span
            key={i}
            className="inline-block h-3 w-3 rounded-full transition-all"
            style={{
              backgroundColor: DOT_COLORS[i % DOT_COLORS.length],
              transform: `scale(${1 + (i / value) * 0.3})`,
              opacity: 0.7 + (i / value) * 0.3,
            }}
          />
        ))}
      </div>
    </div>
  );
}
