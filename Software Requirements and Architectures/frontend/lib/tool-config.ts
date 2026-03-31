import {
  Sun,
  Contrast,
  Droplet,
  Binary,
  RotateCcw,
  Scaling,
  Frame,
  Signature,
  Crop,
  ArrowBigUpDash,
  ImageOff,
  CaseSensitive,
  Box,
  Users,
} from "lucide-react";
import { ToolNames } from "@/lib/tool-types";

// Tool icons mapping - matches toolbar icons exactly
export const TOOL_ICONS: Record<ToolNames, React.ElementType> = {
  brightness: Sun,
  contrast: Contrast,
  saturation: Droplet,
  binarization: Binary,
  rotate: RotateCcw,
  resize: Scaling,
  scale: Scaling,
  border: Frame,
  watermark: Signature,
  cut: Crop,
  cut_ai: Crop,
  upgrade_ai: ArrowBigUpDash,
  bg_remove_ai: ImageOff,
  text_ai: CaseSensitive,
  obj_ai: Box,
  people_ai: Users,
  project: Sun, // fallback
};

// Tool display names - matches toolbar labels exactly
export const TOOL_NAMES: Record<ToolNames, string> = {
  brightness: "Brightness",
  contrast: "Contrast",
  saturation: "Saturation",
  binarization: "Black & White",
  rotate: "Rotate",
  resize: "Resize",
  scale: "Scale",
  border: "Create Border",
  watermark: "Watermark",
  cut: "Crop",
  cut_ai: "AI Crop",
  upgrade_ai: "AI Upgrade",
  bg_remove_ai: "AI Background Removal",
  text_ai: "AI Text Detection",
  obj_ai: "AI Object Detection",
  people_ai: "AI People Detection",
  project: "Project",
};

// Check if tool is AI-based
export const isAITool = (procedure: ToolNames): boolean => {
  return ["cut_ai", "upgrade_ai", "bg_remove_ai", "text_ai", "obj_ai", "people_ai"].includes(procedure);
};
