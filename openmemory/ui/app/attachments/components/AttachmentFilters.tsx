"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FiTrash2 } from "react-icons/fi";
import { GoPlus } from "react-icons/go";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import { clearSelection } from "@/store/attachmentsSlice";
import { useAttachmentsApi } from "@/hooks/useAttachmentsApi";
import { useRouter, useSearchParams } from "next/navigation";
import { debounce } from "lodash";
import { useEffect, useRef, useState } from "react";
import { AttachmentDialog } from "./AttachmentDialog";
import { AttachmentSort } from "./AttachmentSort";

export function AttachmentFilters() {
  const dispatch = useDispatch();
  const selectedAttachmentIds = useSelector(
    (state: RootState) => state.attachments.selectedAttachmentIds
  );
  const { deleteAttachment } = useAttachmentsApi();
  const router = useRouter();
  const searchParams = useSearchParams();
  const inputRef = useRef<HTMLInputElement>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"view" | "edit" | "create">("create");

  const handleDeleteSelected = async () => {
    const confirmDelete = window.confirm(
      `Delete ${selectedAttachmentIds.length} selected attachments? This action cannot be undone.`
    );
    if (!confirmDelete) return;

    try {
      await Promise.all(selectedAttachmentIds.map(id => deleteAttachment(id)));
      dispatch(clearSelection());
      // Trigger refresh
      setTimeout(() => window.location.reload(), 500);
    } catch (error) {
      console.error("Failed to delete attachments:", error);
    }
  };

  const handleSearch = debounce(async (query: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (query) {
      params.set("search", query);
    } else {
      params.delete("search");
    }
    params.set("page", "1"); // Reset to page 1 on search
    router.push(`/attachments?${params.toString()}`);
  }, 500);

  const handleCreate = () => {
    setDialogMode("create");
    setDialogOpen(true);
  };

  useEffect(() => {
    // Set initial search value from URL
    if (searchParams.get("search")) {
      if (inputRef.current) {
        inputRef.current.value = searchParams.get("search") || "";
        inputRef.current.focus();
      }
    }
  }, [searchParams]);

  return (
    <>
      <AttachmentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        attachmentId={undefined}
      />
      <div className="flex flex-col md:flex-row gap-4 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <Input
            ref={inputRef}
            placeholder="Search by content or UUID..."
            className="pl-8 bg-zinc-950 border-zinc-800 max-w-[500px]"
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <AttachmentSort />
          <Button
            onClick={handleCreate}
            className="bg-primary hover:bg-primary/90 text-white"
          >
            <GoPlus className="mr-2" />
            Create Attachment
          </Button>
          {selectedAttachmentIds.length > 0 && (
            <Button
              variant="destructive"
              onClick={handleDeleteSelected}
            >
              <FiTrash2 className="mr-2 h-4 w-4" />
              Delete Selected ({selectedAttachmentIds.length})
            </Button>
          )}
        </div>
      </div>
    </>
  );
}
