"use client";

import { useState, useMemo } from "react";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ImageIcon,
  Layers,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { PipelineStep } from "./pipeline-step";
import { useProjectInfo } from "@/providers/project-provider";
import { useSession } from "@/providers/session-provider";
import {
  useUpdateProjectToolsOrder,
} from "@/lib/mutations/projects";
import { cn } from "@/lib/utils";

interface PipelineSidebarProps {
  disabled?: boolean;
  className?: string;
}

export function PipelineSidebar({
  disabled = false,
  className,
}: PipelineSidebarProps) {
  const project = useProjectInfo();
  const session = useSession();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const updateToolsOrder = useUpdateProjectToolsOrder(
    session.user._id,
    project._id,
    session.token
  );

  // Sort tools by position
  const sortedTools = useMemo(() => {
    return [...project.tools].sort((a, b) => a.position - b.position);
  }, [project.tools]);

  // Count AI tools
  const aiToolCount = useMemo(() => {
    return sortedTools.filter((t) =>
      ["cut_ai", "upgrade_ai", "bg_remove_ai", "text_ai", "obj_ai", "people_ai"].includes(
        t.procedure
      )
    ).length;
  }, [sortedTools]);

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

    const reorderedTools = [...sortedTools];
    const [movedTool] = reorderedTools.splice(draggedIndex, 1);
    reorderedTools.splice(dropIndex, 0, movedTool);

    const toolsWithNewPositions = reorderedTools.map((tool, idx) => ({
      _id: tool._id,
      position: idx,
      procedure: tool.procedure,
      params: tool.params,
    }));

    updateToolsOrder.mutate({
      uid: session.user._id,
      pid: project._id,
      token: session.token,
      tools: toolsWithNewPositions,
    });

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const isEmpty = sortedTools.length === 0;
  const hasImages = project.imgs.length > 0;

  // Collapsed view
  if (isCollapsed) {
    return (
      <div
        className={cn(
          "flex flex-col items-center py-4 px-2 border-l bg-background h-full w-12",
          className
        )}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="mb-4"
              onClick={() => setIsCollapsed(false)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">Expand Pipeline</TooltipContent>
        </Tooltip>

        <div className="flex flex-col items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center justify-center w-8 h-8 rounded-md bg-primary/10">
                <Layers className="h-4 w-4 text-primary" />
              </div>
            </TooltipTrigger>
            <TooltipContent side="left">
              Pipeline ({sortedTools.length} steps)
            </TooltipContent>
          </Tooltip>

          {!isEmpty && (
            <Badge variant="secondary" className="h-6 w-6 p-0 justify-center">
              {sortedTools.length}
            </Badge>
          )}

          {aiToolCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center justify-center w-6 h-6 rounded-md bg-gradient-to-r from-purple-500/20 to-pink-500/20">
                  <Sparkles className="h-3 w-3 text-purple-600" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="left">{aiToolCount} AI tools</TooltipContent>
            </Tooltip>
          )}
        </div>

        <div className="flex-1" />
      </div>
    );
  }

  // Expanded view
  return (
    <div
      className={cn(
        "flex flex-col border-l bg-background h-full w-72",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-primary" />
          <h2 className="font-semibold">Pipeline</h2>
          {!isEmpty && (
            <Badge variant="secondary">{sortedTools.length}</Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setIsCollapsed(true)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full p-4 text-center">
            <div className="rounded-full bg-muted p-4 mb-4">
              <Layers className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium mb-1">No tools added</h3>
            <p className="text-sm text-muted-foreground">
              Add tools from the toolbar on the left to build your image
              processing pipeline.
            </p>
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div className="p-3">

              {/* AI tools badge */}
              {aiToolCount > 0 && (
                <div className="mb-3">
                  <Badge
                    variant="secondary"
                    className="w-full justify-center bg-gradient-to-r from-purple-500/10 to-pink-500/10 text-purple-700 dark:text-purple-300"
                  >
                    {aiToolCount} AI-powered step{aiToolCount !== 1 ? "s" : ""}
                  </Badge>
                </div>
              )}

              {/* Pipeline steps */}
              <div className="flex flex-col gap-3">
                {sortedTools.map((tool, index) => (
                  <PipelineStep
                    key={tool._id}
                    tool={tool}
                    index={index}
                    isFirst={index === 0}
                    isLast={index === sortedTools.length - 1}
                    isDragging={draggedIndex === index}
                    isDragOver={dragOverIndex === index}
                    onDragStart={handleDragStart}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onDragEnd={handleDragEnd}
                    disabled={disabled}
                  />
                ))}
              </div>
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
