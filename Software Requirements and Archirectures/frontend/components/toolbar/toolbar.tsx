import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import BrightnessTool from "./brightness-tool";
import ContrastTool from "./contrast-tool";
import CropTool from "./crop-tool";
import ResizeTool from "./resize-tool";
import RotateTool from "./rotate-tool";
import SaturationTool from "./saturation-tool";
import BorderTool from "./border-tool";
import BinarizationTool from "./binarization-tool";
import WatermarkTool from "./watermark-tool";
import CropAITool from "./ai-crop-tool";
import BgRemovalAITool from "./ai-bg-removal";
import ObjectAITool from "./object-ai-tool";
import PeopleAITool from "./people-ai-tool";
import TextAITool from "./text-ai-tool";
import UpgradeAITool from "./upgrade-ai-tool";
import { useClearProjectTools, useUpdateProjectToolsOrder } from "@/lib/mutations/projects";
import { useSession } from "@/providers/session-provider";
import { useProjectInfo } from "@/providers/project-provider";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import { Eraser, GripVertical } from "lucide-react";
import { ToolNames } from "@/lib/tool-types";

const TOOL_COMPONENTS: Partial<
  Record<ToolNames, React.ComponentType<{ disabled: boolean }>>
> = {
  brightness: BrightnessTool,
  contrast: ContrastTool,
  saturation: SaturationTool,
  binarization: BinarizationTool,
  rotate: RotateTool,
  cut: CropTool,
  resize: ResizeTool,
  border: BorderTool,
  watermark: WatermarkTool,
  cut_ai: CropAITool,
  bg_remove_ai: BgRemovalAITool,
  obj_ai: ObjectAITool,
  people_ai: PeopleAITool,
  text_ai: TextAITool,
  upgrade_ai: UpgradeAITool,
};

const DEFAULT_TOOL_ORDER: ToolNames[] = [
  "brightness", "contrast", "saturation", "binarization", "rotate", "resize", "border", "watermark", "cut", "scale", "cut_ai", "upgrade_ai", "bg_remove_ai", "text_ai", "obj_ai", "people_ai"
];

export function Toolbar() {
  const searchParams = useSearchParams();
  const view = searchParams.get("view") ?? "grid";
  const disabled = view === "grid";
  const project = useProjectInfo();
  const session = useSession();

  const [open, setOpen] = useState<boolean>(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [toolOrder, setToolOrder] = useState<ToolNames[]>(() => {
    if (
      typeof window === "undefined" ||
      !session?.user?._id
    ) {
      return DEFAULT_TOOL_ORDER;
    }

    const saved = localStorage.getItem(
      `tool-order:${session.user._id}`
    );

    try {
      return saved ? JSON.parse(saved) : DEFAULT_TOOL_ORDER;
    } catch {
      return DEFAULT_TOOL_ORDER;
    }
  });

  useEffect(() => {
    if (!session?.user?._id) return;

    localStorage.setItem(
      `tool-order:${session.user._id}`,
      JSON.stringify(toolOrder)
    );
  }, [toolOrder, session.user._id]);

  const clearTools = useClearProjectTools(
    session.user._id,
    project._id,
    session.token,
  );

  const updateToolsOrder = useUpdateProjectToolsOrder(
    session.user._id,
    project._id,
    session.token,
  );

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", index.toString());
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();

    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    const reorderedTools = [...toolOrder];
    const [movedTool] = reorderedTools.splice(draggedIndex, 1);
    reorderedTools.splice(dropIndex, 0, movedTool);

    setToolOrder(reorderedTools);

    if (project.tools.length > 0) {
      const toolsWithNewPositions = project.tools.map((tool) => {
        const newPosition = reorderedTools.indexOf(tool.procedure);
        return {
          _id: tool._id,
          position: newPosition,
          procedure: tool.procedure,
          params: tool.params,
        };
      }).sort((a, b) => a.position - b.position);

      updateToolsOrder.mutate({
        uid: session.user._id,
        pid: project._id,
        token: session.token,
        tools: toolsWithNewPositions,
      });
    }

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  return (
    <div className="flex h-full w-20 flex-col justify-between items-center border-r bg-background p-2 overflow-y-auto overflow-x-hidden no-scrollbar">
      <div className="flex flex-col gap-2">
        <span className="text-sm text-gray-500">Tools</span>

        {toolOrder.map((procedure, index) => {
          const ToolComponent = TOOL_COMPONENTS[procedure];
          if (!ToolComponent) {
            console.warn("No component for tool:", procedure);
            return null;
          }

          const isDragging = draggedIndex === index;
          const isDraggedOver = dragOverIndex === index;

          return (
            <div
              key={procedure}
              draggable={!disabled}
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              className={`group relative flex items-center ${isDragging ? "opacity-50" : ""
                } ${isDraggedOver ? "border-t-2 border-primary" : ""}`}>
              {!disabled && (
                <GripVertical
                  className="
                  h-3 w-3
                  mr-1
                  cursor-grab
                  text-gray-400
                  opacity-0
                  transition-opacity
                  group-hover:opacity-100
                  active:cursor-grabbing
                "
                  onMouseDown={(e) => e.stopPropagation()}
                />
              )}
              <ToolComponent disabled={disabled} />
            </div>
          );
        })}
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button
            variant="outline"
            className="text-red-400 size-8"
            disabled={project.tools.length === 0}
          >
            <Eraser />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear Tools?</DialogTitle>
            <DialogDescription>
              This will remove <b>all</b> edits from the current project.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="destructive"
              onClick={() => {
                clearTools.mutate({
                  uid: session.user._id,
                  pid: project._id,
                  toolIds: project.tools.map((t) => t._id),
                  token: session.token,
                });
                setOpen(false);
              }}
            >
              Clear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}