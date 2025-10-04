"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { useState, useRef } from "react";
import { GoPlus } from "react-icons/go";
import { Loader2 } from "lucide-react";
import { useMemoriesApi } from "@/hooks/useMemoriesApi";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";

export function CreateMemoryDialog() {
  const { createMemory, isLoading, fetchMemories } = useMemoriesApi();
  const [open, setOpen] = useState(false);
  const [hasAttachment, setHasAttachment] = useState(false);
  const [useExistingAttachment, setUseExistingAttachment] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const attachmentTextRef = useRef<HTMLTextAreaElement>(null);
  const attachmentIdRef = useRef<HTMLInputElement>(null);

  const handleCreateMemory = async (text: string) => {
    try {
      let attachmentText: string | undefined;
      let attachmentId: string | undefined;

      if (hasAttachment) {
        if (useExistingAttachment) {
          attachmentId = attachmentIdRef.current?.value.trim();
          if (!attachmentId) {
            toast.error("Please enter an attachment ID");
            return;
          }
        } else {
          attachmentText = attachmentTextRef.current?.value.trim();
          if (!attachmentText) {
            toast.error("Please enter attachment content");
            return;
          }
        }
      }

      await createMemory(text, attachmentText, attachmentId);
      toast.success("Memory created successfully");
      // Reset and close
      setOpen(false);
      setHasAttachment(false);
      setUseExistingAttachment(false);
      // refetch memories
      await fetchMemories();
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "Failed to create memory");
    }
  };

  const handleDialogChange = (isOpen: boolean) => {
    setOpen(isOpen);
    if (!isOpen) {
      // Reset state when closing
      setHasAttachment(false);
      setUseExistingAttachment(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleDialogChange}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="bg-primary hover:bg-primary/90 text-white"
        >
          <GoPlus />
          Create Memory
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] overflow-y-auto bg-zinc-900 border-zinc-800">
        <DialogHeader>
          <DialogTitle>Create New Memory</DialogTitle>
          <DialogDescription>
            Add a new memory to your OpenMemory instance
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="memory">Memory (Summary)</Label>
            <Textarea
              ref={textRef}
              id="memory"
              placeholder="e.g., Lives in San Francisco"
              className="bg-zinc-950 border-zinc-800 min-h-[100px]"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="has-attachment"
              checked={hasAttachment}
              onCheckedChange={(checked) => {
                setHasAttachment(checked as boolean);
                if (!checked) {
                  setUseExistingAttachment(false);
                }
              }}
            />
            <Label
              htmlFor="has-attachment"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
            >
              Add extended content (attachment)
            </Label>
          </div>

          {hasAttachment && (
            <div className="grid gap-4 pl-6 border-l-2 border-zinc-700">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="use-existing"
                  checked={useExistingAttachment}
                  onCheckedChange={(checked) =>
                    setUseExistingAttachment(checked as boolean)
                  }
                />
                <Label
                  htmlFor="use-existing"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Link existing attachment (by ID)
                </Label>
              </div>

              {useExistingAttachment ? (
                <div className="grid gap-2">
                  <Label htmlFor="attachment-id">Attachment ID</Label>
                  <Input
                    ref={attachmentIdRef}
                    id="attachment-id"
                    placeholder="Enter UUID or custom ID"
                    className="bg-zinc-950 border-zinc-800 font-mono text-sm"
                  />
                </div>
              ) : (
                <div className="grid gap-2">
                  <Label htmlFor="attachment-text">Extended Content</Label>
                  <Textarea
                    ref={attachmentTextRef}
                    id="attachment-text"
                    placeholder="Enter extended content here (will be auto-saved as attachment)..."
                    className="bg-zinc-950 border-zinc-800 min-h-[150px] font-mono text-sm"
                  />
                  <div className="text-xs text-zinc-500">
                    This will create a new attachment automatically
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            disabled={isLoading}
            onClick={() => handleCreateMemory(textRef?.current?.value || "")}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              "Save Memory"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
