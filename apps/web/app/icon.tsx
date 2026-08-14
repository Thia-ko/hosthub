import { ImageResponse } from "next/og";
import { FALLBACK_PRIMARY_COLOR, getThemeSettings } from "@/lib/theme-settings";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default async function Icon() {
  const theme = await getThemeSettings();
  const brandPrimary = theme?.light_primary_color ?? FALLBACK_PRIMARY_COLOR;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: brandPrimary,
          borderRadius: 7,
        }}
      >
        <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
          <rect x="8" y="8" width="8" height="8" rx="2.1" stroke="white" strokeWidth="1.8" />
          <path
            d="M12 8V4.9M8.7 14.8 6 17.4M15.3 14.8l2.7 2.6"
            stroke="white"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <circle cx="12" cy="3.7" r="1.5" fill="white" />
          <circle cx="4.9" cy="18.5" r="1.5" fill="white" />
          <circle cx="19.1" cy="18.5" r="1.5" fill="white" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
