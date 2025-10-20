"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useEffect, useRef, useState } from "react";
import { Loader2, ChevronDown } from "lucide-react";
import { useMemoriesApi } from "@/hooks/useMemoriesApi";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";
import { usePathname } from "next/navigation";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { getCustomMetadata, validateCustomMetadata } from "@/lib/metadata";

interface UpdateMemoryProps {
  memoryId: string;
  memoryContent: string;
  memoryMetadata?: Record<string, any>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const UpdateMemory = ({
  memoryId,
  memoryContent,
  memoryMetadata,
  open,
  onOpenChange,
}: UpdateMemoryProps) => {
  const { updateMemory, isLoading, fetchMemories, fetchMemoryById } =
    useMemoriesApi();
  const textRef = useRef<HTMLTextAreaElement>(null);
  const metadataRef = useRef<HTMLTextAreaElement>(null);
  const pathname = usePathname();
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [metadataJson, setMetadataJson] = useState("");
  const [metadataError, setMetadataError] = useState("");

  useEffect(() => {
    if (open) {
      const customMetadata = getCustomMetadata(memoryMetadata) || {};
      setMetadataJson(JSON.stringify(customMetadata, null, 2));
      setMetadataError("");
    }
  }, [open, memoryMetadata]);

  const handleUpdateMemory = async (text: string) => {
    try {
      let metadata: Record<string, any> | undefined;

      // Parse and validate metadata JSON if provided
      if (metadataJson.trim()) {
        try {
          metadata = JSON.parse(metadataJson);

          // Validate that no system fields are being modified
          const validationError = validateCustomMetadata(metadata);
          if (validationError) {
            setMetadataError(validationError);
            return;
          }
        } catch (e) {
          setMetadataError("Invalid JSON format");
          return;
        }
      }

      await updateMemory(memoryId, text, metadata);
      toast.success("Memory updated successfully");
      onOpenChange(false);
      if (pathname.includes("memories")) {
        await fetchMemories();
      } else {
        await fetchMemoryById(memoryId);
      }
    } catch (error) {
      console.error(error);
      toast.error("Failed to update memory");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px] bg-zinc-900 border-zinc-800 z-50">
        <DialogHeader>
          <DialogTitle>Update Memory</DialogTitle>
          <DialogDescription>Edit your existing memory</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="memory">Memory</Label>
            <Textarea
              ref={textRef}
              id="memory"
              className="bg-zinc-950 border-zinc-800 min-h-[150px]"
              defaultValue={memoryContent}
            />
          </div>

          <div className="grid gap-2">
            <Collapsible open={metadataOpen} onOpenChange={setMetadataOpen}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors">
                <ChevronDown className={`h-4 w-4 transition-transform ${metadataOpen ? 'rotate-180' : ''}`} />
                <span>Metadata (Optional)</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3">
                <Label htmlFor="metadata" className="text-xs text-zinc-400">
                  Custom metadata as JSON (system fields like user_id are automatically preserved)
                </Label>
                <Textarea
                  ref={metadataRef}
                  id="metadata"
                  className="bg-zinc-950 border-zinc-800 min-h-[120px] font-mono text-sm mt-2"
                  value={metadataJson}
                  onChange={(e) => {
                    setMetadataJson(e.target.value);
                    setMetadataError("");
                  }}
                  placeholder='{\n  "type": "notes",\n  "category": "example"\n}'
                />
                {metadataError && (
                  <p className="text-xs text-red-400 mt-1">{metadataError}</p>
                )}
              </CollapsibleContent>
            </Collapsible>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            className="w-[140px]"
            disabled={isLoading}
            onClick={() => handleUpdateMemory(textRef?.current?.value || "")}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              "Update Memory"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UpdateMemory;
