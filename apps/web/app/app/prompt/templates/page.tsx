import type { Metadata } from "next";
import PromptTemplateGalleryView from "./view";

export const metadata: Metadata = { title: "Templates de prompt | Hosthub" };

export default function PromptTemplateGalleryPage() {
  return <PromptTemplateGalleryView />;
}
