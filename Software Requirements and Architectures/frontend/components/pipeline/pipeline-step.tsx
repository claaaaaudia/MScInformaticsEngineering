"use client";

import { useState } from "react";
import { GripVertical, Pencil, Trash2, X, Check, Box } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ProjectToolResponse } from "@/lib/projects";
import { ToolNames } from "@/lib/tool-types";
import { TOOL_ICONS, TOOL_NAMES, isAITool } from "@/lib/tool-config";
import { cn } from "@/lib/utils";

// Format tool parameters for display
const formatParams = (procedure: ToolNames, params: Record<string, unknown>): string => {
  switch (procedure) {
    case "brightness":
      return `${Math.round(((params.brightness as number) - 1) * 100)}%`;
    case "contrast":
      return `${Math.round(((params.contrastFactor as number) - 1) * 100)}%`;
    case "saturation":
      return `${Math.round(((params.saturationFactor as number) - 1) * 100)}%`;
    case "binarization":
      return `Threshold: ${params.threshold}`;
    case "rotate":
      return `${params.degrees}°`;
    case "resize":
      return `${params.width}x${params.height}`;
    case "border":
      return `${params.borderWidth}px`;
    default:
      return "";
  }
};

interface PipelineStepProps {
  tool: ProjectToolResponse;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  isDragging?: boolean;
  isDragOver?: boolean;
  onEdit?: (tool: ProjectToolResponse) => void;
  onDelete?: (toolId: string) => void;
  onDragStart?: (e: React.DragEvent, index: number) => void;
  onDragOver?: (e: React.DragEvent, index: number) => void;
  onDragLeave?: () => void;
  onDrop?: (e: React.DragEvent, index: number) => void;
  onDragEnd?: () => void;
  disabled?: boolean;
}

export function PipelineStep({
  tool,
  index,
  isFirst,
  isLast,
  isDragging = false,
  isDragOver = false,
  onEdit,
  onDelete,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  onDragEnd,
  disabled = false,
}: PipelineStepProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const Icon = TOOL_ICONS[tool.procedure] || Box;
  const displayName = TOOL_NAMES[tool.procedure] || tool.procedure;
  const paramString = formatParams(tool.procedure, tool.params as Record<string, unknown>);
  const isAI = isAITool(tool.procedure);

  const handleDeleteClick = () => {
    if (showDeleteConfirm) {
      onDelete?.(tool._id);
      setShowDeleteConfirm(false);
    } else {
      setShowDeleteConfirm(true);
    }
  };

  return (
    <div className="relative">
      {/* Connection line to previous step */}
      {!isFirst && (
        <div className="absolute left-6 -top-3 w-0.5 h-3 bg-border" />
      )}
      
      <Card
        draggable={!disabled}
        onDragStart={(e) => onDragStart?.(e, index)}
        onDragOver={(e) => onDragOver?.(e, index)}
        onDragLeave={onDragLeave}
        onDrop={(e) => onDrop?.(e, index)}
        onDragEnd={onDragEnd}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => {
          setIsHovered(false);
          setShowDeleteConfirm(false);
        }}
        className={cn(
          "relative flex items-center gap-3 p-3 transition-all duration-200",
          isDragging && "opacity-50 scale-95",
          isDragOver && "border-primary border-2 bg-primary/5",
          isHovered && !disabled && "shadow-md",
          disabled && "opacity-60 cursor-not-allowed"
        )}
      >
        {/* Drag handle */}
        {!disabled && (
          <div className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground transition-colors">
            <GripVertical className="h-4 w-4" />
          </div>
        )}

        {/* Step number */}
        <div className={cn(
          "flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium",
          isAI ? "bg-gradient-to-br from-purple-500 to-pink-500 text-white" : "bg-primary text-primary-foreground"
        )}>
          {index + 1}
        </div>

        {/* Tool icon and info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm truncate">{displayName}</span>
            {isAI && (
              <Badge variant="secondary" className="text-xs px-1.5 py-0 h-5 bg-gradient-to-r from-purple-500/10 to-pink-500/10 text-purple-700 dark:text-purple-300">
                AI
              </Badge>
            )}
          </div>
          {paramString && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">
              {paramString}
            </p>
          )}
        </div>

        {/* Action buttons */}
        {!disabled && (
          <div className="flex items-center gap-1">
            {onEdit && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      "h-7 w-7 transition-opacity duration-200",
                      isHovered ? "opacity-100" : "opacity-0"
                    )}
                    onClick={() => onEdit(tool)}
                    tabIndex={isHovered ? 0 : -1}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Edit</TooltipContent>
              </Tooltip>
            )}
            {onDelete && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={showDeleteConfirm ? "destructive" : "ghost"}
                    size="icon"
                    className={cn(
                      "h-7 w-7 transition-opacity duration-200",
                      isHovered ? "opacity-100" : "opacity-0"
                    )}
                    onClick={handleDeleteClick}
                    tabIndex={isHovered ? 0 : -1}
                  >
                    {showDeleteConfirm ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {showDeleteConfirm ? "Confirm delete" : "Delete"}
                </TooltipContent>
              </Tooltip>
            )}
            {showDeleteConfirm && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      "h-7 w-7 transition-opacity duration-200",
                      isHovered ? "opacity-100" : "opacity-0"
                    )}
                    onClick={() => setShowDeleteConfirm(false)}
                    tabIndex={isHovered ? 0 : -1}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Cancel</TooltipContent>
              </Tooltip>
            )}
          </div>
        )}
      </Card>

      {/* Connection line to next step */}
      {!isLast && (
        <div className="absolute left-6 -bottom-3 w-0.5 h-3 bg-border" />
      )}
    </div>
  );
}
