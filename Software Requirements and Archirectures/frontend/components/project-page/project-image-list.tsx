"use client";

import { useState, useEffect } from "react";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel";
import { useGetSocket } from "@/lib/queries/projects";
import { useProjectInfo } from "@/providers/project-provider";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/providers/session-provider";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogContent,
  DialogFooter,
} from "../ui/dialog";
import Image from "next/image";
import { useToast } from "@/hooks/use-toast";
import * as ProjectTypes from "@/lib/projects";
import { ProjectImage } from "./project-image";
import { useQueryClient } from "@tanstack/react-query";
import ProjectText from "./project-text";

export function ProjectImageList({
  setCurrentImageId,
  results,
}: {
  setCurrentImageId: (img: ProjectTypes.ProjectImage) => void;
  results: {
    imgs: ProjectTypes.ProjectImage[];
    texts: ProjectTypes.ProjectImageText[];
  };
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const view = searchParams.get("view") ?? "grid";
  const mode = searchParams.get("mode") ?? "edit";

  const [api, setApi] = useState<CarouselApi>();
  const [current, setCurrent] = useState(0);
  const [count, setCount] = useState(0);
  const [jumpTo, setJumpTo] = useState<number | null>(null);
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState<string[] | null>(null);

  const project = useProjectInfo();
  const session = useSession();
  const { toast } = useToast();

  const qc = useQueryClient();
  const socket = useGetSocket(session.token);

  const displayImages =
    results.imgs.length > 0 ? results.imgs : project.imgs;

  useEffect(() => {
    let active = true;

    if (active && socket.data) {
      socket.data.on("preview-error", (msg) => {
        if (!active) return;
        const msg_content = JSON.parse(msg);
        toast({
          title: "Ups! An error occurred.",
          description: `${msg_content.error_code}: ${msg_content.error_msg}`,
          variant: "destructive",
        });
      });

      socket.data.on("preview-ready", (msg) => {
        if (!active) return;
        const msg_content = JSON.parse(msg) as {
          imageUrl: string;
          textResults: string[];
        };
        setPreviewImage(msg_content.imageUrl);
        setPreviewText(msg_content.textResults);
        setPreviewOpen(true);
      });
    }

    return () => {
      active = false;
      socket.data?.off("preview-error");
      socket.data?.off("preview-ready");
    };
  }, [socket.data, toast]);

  useEffect(() => {
    if (view === "grid") {
      setApi(undefined);
      setJumpTo(null);
    }
  }, [view]);

useEffect(() => {
  if (!api) return;

  setCount(api.scrollSnapList().length);
  setCurrent(api.selectedScrollSnap() + 1);

  if (displayImages.length > 0) {
    setCurrentImageId(displayImages[api.selectedScrollSnap()]);
  }

  const handleSelect = () => {
    setCurrent(api.selectedScrollSnap() + 1);
    if (displayImages.length > 0) {
      setCurrentImageId(displayImages[api.selectedScrollSnap()]);
    }
  };

  api.on("select", handleSelect);

  if (jumpTo !== null && jumpTo !== api.selectedScrollSnap()) {
    api.scrollTo(jumpTo, true);
    setJumpTo(null);
  }

  return () => {
    api.off("select", handleSelect);
  };
}, [api, jumpTo, displayImages, setCurrentImageId]);

  return (
    <Dialog
      open={previewOpen}
      onOpenChange={() => {
        setPreviewOpen(false);
        setPreviewImage(null);
      }}
    >
      <div className="size-full">
        {view === "grid" || displayImages.length <= 0 ? (
          // Grid view
          <div className="size-full flex flex-col items-center">
            {displayImages.length > 0 || results.texts.length > 0 ? (
              <>
                {mode !== "results" && (
                  <div className="relative pt-4 pb-2 text-gray-500 text-sm w-full text-center">
                    To start editing, select an image from the grid.
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2 p-2 overflow-scroll overflow-x-hidden h-fit">
                  {displayImages.map((image, index) => (
                    <button
                      key={image._id}
                      className="aspect-square"
                      onClick={() => {
                        setJumpTo(index);
                        router.push(`?mode=${mode}&view=carousel`);
                        qc.invalidateQueries({
                          queryKey: ["socket"],
                          refetchType: "all",
                        });
                      }}
                    >
                      <ProjectImage image={image} />
                    </button>
                  ))}
                  {results.texts.map((text, index) => (
                    <button
                      key={text._id + index}
                      className="aspect-square"
                      onClick={() => {
                        setJumpTo(displayImages.length + index);
                        router.push(`?mode=${mode}&view=carousel`);
                        qc.invalidateQueries({
                          queryKey: ["socket"],
                          refetchType: "all",
                        });
                      }}
                    >
                      <ProjectText text={text.text} />
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full">
                <p className="text-gray-500 text-xl">
                  Add some images to start.
                </p>
              </div>
            )}
          </div>
        ) : (
          // Carousel view
          <div className="size-full px-2 sm:px-16 py-2">
            <Carousel setApi={setApi}>
              <CarouselContent className="aspect-auto h-[calc(100vh-99px-0.5rem-36px)] xl:h-[calc(100vh-55px-0.5rem-36px)]">
                {displayImages.map((image) => (
                  <CarouselItem key={image._id}>
                    <ProjectImage image={image} animation={false} />
                  </CarouselItem>
                ))}
                {results.texts.map((text) => (
                  <CarouselItem key={text.name}>
                    <ProjectText text={text.text} />
                  </CarouselItem>
                ))}
              </CarouselContent>
              <CarouselPrevious className="hidden sm:flex" />
              <CarouselNext className="hidden sm:flex" />
            </Carousel>
            <div className="py-2 text-center text-sm text-muted-foreground">
              {current} / {count}
            </div>
          </div>
        )}
      </div>

      <DialogContent className="max-w-[80%] mt-4 overflow-y-scroll overflow-x-hidden">
        <DialogHeader>
          <DialogTitle>Image Preview</DialogTitle>
        </DialogHeader>
        <div className="flex justify-center items-center">
          {previewImage && (
            <Image
              src={previewImage}
              width={500}
              height={500}
              className={`object-contain rounded-md w-full ${
                previewText ? "max-h-[60vh]" : "max-h-[80vh]"
              }`}
              alt="Preview"
              unoptimized
            />
          )}
        </div>
        {previewText && previewText.length > 0 && (
          <DialogFooter>
            <div className="flex flex-col gap-2 w-full h-96">
              {previewText.map((text, index) => (
                <iframe
                  src={text}
                  key={index}
                  className="size-full"
                />
              ))}
            </div>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
