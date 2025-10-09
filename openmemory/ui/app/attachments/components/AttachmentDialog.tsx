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
import { useState, useEffect } from "react";
import { Loader2, Copy, Check } from "lucide-react";
import { useAttachmentsApi } from "@/hooks/useAttachmentsApi";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

interface AttachmentDialogProps {
  attachmentId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "view" | "edit" | "create";
}

export function AttachmentDialog({
  attachmentId,
  open,
  onOpenChange,
  mode,
}: AttachmentDialogProps) {
  const {
    fetchAttachment,
    createAttachment,
    updateAttachment,
    deleteAttachment,
    isLoading,
  } = useAttachmentsApi();

  const [content, setContent] = useState("");
  const [customId, setCustomId] = useState("");
  const [isEditing, setIsEditing] = useState(mode === "create" || mode === "edit");
  const [createdAt, setCreatedAt] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open && attachmentId && mode !== "create") {
      loadAttachment();
    } else if (!open) {
      // Reset state when dialog closes
      setContent("");
      setCustomId("");
      setIsEditing(mode === "create");
      setCreatedAt("");
      setUpdatedAt("");
    }
  }, [open, attachmentId, mode]);

  const loadAttachment = async () => {
    if (!attachmentId) return;
    try {
      const attachment = await fetchAttachment(attachmentId);
      setContent(attachment.content);
      setCreatedAt(attachment.created_at);
      setUpdatedAt(attachment.updated_at);
    } catch (error) {
      toast.error("Failed to load attachment");
    }
  };

  const validateUUID = (uuid: string): boolean => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  };

  const handleSave = async () => {
    // Validate custom UUID if provided
    if (mode === "create" && customId && !validateUUID(customId)) {
      toast.error("Invalid UUID format. Please use a valid UUID or leave empty to auto-generate.");
      return;
    }

    try {
      if (mode === "create") {
        await createAttachment(content, customId || undefined);
        toast.success("Attachment created successfully");
        // Auto-reload the page to show new attachment
        setTimeout(() => window.location.reload(), 500);
      } else if (attachmentId) {
        await updateAttachment(attachmentId, content);
        toast.success("Attachment updated successfully");
        await loadAttachment();
        // Auto-reload the page to reflect changes
        setTimeout(() => window.location.reload(), 500);
      }
      setIsEditing(false);
      if (mode === "create") {
        onOpenChange(false);
      }
    } catch (error: any) {
      toast.error(error.message || "Failed to save attachment");
    }
  };

  const handleDelete = async () => {
    if (!attachmentId) return;

    // Modern confirmation using toast
    const confirmDelete = window.confirm("Are you sure you want to delete this attachment? This action cannot be undone.");
    if (!confirmDelete) return;

    try {
      await deleteAttachment(attachmentId);
      toast.success("Attachment deleted successfully");
      onOpenChange(false);
      // Auto-reload the page to reflect deletion
      setTimeout(() => window.location.reload(), 500);
    } catch (error) {
      toast.error("Failed to delete attachment");
    }
  };

  const handleCopyId = () => {
    if (attachmentId) {
      navigator.clipboard.writeText(attachmentId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success("ID copied to clipboard");
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "";
    return new Date(dateString).toLocaleString();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[80vh] bg-zinc-900 border-zinc-800">
        <DialogHeader>
          <DialogTitle>
            {mode === "create"
              ? "Create New Attachment"
              : isEditing
              ? "Edit Attachment"
              : "View Attachment"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Create extended content that can be linked to memories"
              : isEditing
              ? "Edit the attachment content"
              : "View attachment details"}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4 overflow-y-auto">
          {attachmentId && (
            <div className="grid gap-2">
              <Label>ID</Label>
              <div className="flex gap-2">
                <Input
                  value={attachmentId}
                  readOnly
                  className="bg-zinc-950 border-zinc-800 font-mono text-sm"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyId}
                  className="shrink-0"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          )}
          {mode === "create" && (
            <div className="grid gap-2">
              <Label htmlFor="custom-id">Custom ID (optional)</Label>
              <Input
                id="custom-id"
                value={customId}
                onChange={(e) => setCustomId(e.target.value)}
                placeholder="Leave empty to auto-generate UUID"
                className="bg-zinc-950 border-zinc-800 font-mono text-sm"
              />
            </div>
          )}
          <div className="grid gap-2">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              readOnly={!isEditing}
              placeholder="Enter extended content here..."
              className="bg-zinc-950 border-zinc-800 min-h-[300px] font-mono text-sm"
            />
            <div className="text-xs text-zinc-500">
              {content.length} characters ({(content.length / 1024).toFixed(2)} KB)
            </div>
          </div>
          {mode !== "create" && createdAt && (
            <div className="grid grid-cols-2 gap-4 text-sm text-zinc-400">
              <div>
                <span className="font-medium">Created:</span> {formatDate(createdAt)}
              </div>
              <div>
                <span className="font-medium">Updated:</span> {formatDate(updatedAt)}
              </div>
            </div>
          )}
        </div>
        <DialogFooter>
          {mode !== "create" && !isEditing && (
            <>
              <Button variant="outline" onClick={() => setIsEditing(true)}>
                Edit
              </Button>
              <Button variant="destructive" onClick={handleDelete} disabled={isLoading}>
                Delete
              </Button>
            </>
          )}
          {(mode === "create" || isEditing) && (
            <>
              <Button
                variant="outline"
                onClick={() => {
                  if (mode === "create") {
                    onOpenChange(false);
                  } else {
                    setIsEditing(false);
                    loadAttachment();
                  }
                }}
              >
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={isLoading || !content.trim()}>
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  "Save"
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
