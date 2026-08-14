import { ImageResponse } from "next/og";
import { FALLBACK_PRIMARY_COLOR, getThemeSettings } from "@/lib/theme-settings";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default async function AppleIcon() {
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
        }}
      >
        <svg width="118" height="118" viewBox="0 0 24 24" fill="none">
          <rect x="8" y="8" width="8" height="8" rx="2.1" stroke="white" strokeWidth="1.6" />
          <path
            d="M12 8V4.9M8.7 14.8 6 17.4M15.3 14.8l2.7 2.6"
            stroke="white"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <circle cx="12" cy="3.7" r="1.4" fill="white" />
          <circle cx="4.9" cy="18.5" r="1.4" fill="white" />
          <circle cx="19.1" cy="18.5" r="1.4" fill="white" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
