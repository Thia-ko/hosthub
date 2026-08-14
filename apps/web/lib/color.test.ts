import { describe, expect, it } from "vitest";
import { hexToOklch } from "@/lib/color";

describe("hexToOklch", () => {
  it("converts pure black to L=0, C=0", () => {
    expect(hexToOklch("#000000")).toBe("0.0000 0.0000 0.00");
  });

  it("converts pure white to L=1, C=0", () => {
    // hue is floating-point noise around 0deg for a truly achromatic color, not a real angle -
    // pin the actual computed value rather than an idealized "0.00".
    expect(hexToOklch("#ffffff")).toBe("1.0000 0.0000 89.88");
  });

  it("matches the known oklch value for pure red", () => {
    expect(hexToOklch("#ff0000")).toBe("0.6280 0.2577 29.23");
  });

  it("is case-insensitive on hex digits", () => {
    expect(hexToOklch("#FF0000")).toBe(hexToOklch("#ff0000"));
  });

  it("falls back to achromatic black for malformed input", () => {
    expect(hexToOklch("not-a-color")).toBe("0 0 0");
    expect(hexToOklch("#fff")).toBe("0 0 0"); // 3-digit shorthand unsupported
    expect(hexToOklch("#gggggg")).toBe("0 0 0");
  });
});
