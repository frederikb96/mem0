"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GoPlus } from "react-icons/go";
import { Search } from "lucide-react";
import { AttachmentDialog } from "./components/AttachmentDialog";
import { toast } from "sonner";
import "@/styles/animation.css";

export default function AttachmentsPage() {
  const searchParams = useSearchParams();
  const [searchId, setSearchId] = useState("");
  const [viewingId, setViewingId] = useState<string | undefined>(undefined);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"view" | "edit" | "create">("view");

  // Auto-open dialog if ID is in URL query params
  useEffect(() => {
    const idFromUrl = searchParams?.get("id");
    if (idFromUrl) {
      setViewingId(idFromUrl);
      setSearchId(idFromUrl);
      setDialogMode("view");
      setDialogOpen(true);
    }
  }, [searchParams]);

  const handleSearch = () => {
    if (!searchId.trim()) {
      toast.error("Please enter an attachment ID");
      return;
    }
    setViewingId(searchId.trim());
    setDialogMode("view");
    setDialogOpen(true);
  };

  const handleCreate = () => {
    setViewingId(undefined);
    setDialogMode("create");
    setDialogOpen(true);
  };

  const handleDialogClose = (open: boolean) => {
    setDialogOpen(open);
    if (!open) {
      setSearchId("");
      setViewingId(undefined);
    }
  };

  return (
    <div className="">
      <AttachmentDialog
        attachmentId={viewingId}
        open={dialogOpen}
        onOpenChange={handleDialogClose}
        mode={dialogMode}
      />
      <main className="flex-1 py-6">
        <div className="container max-w-4xl">
          <div className="mb-8 animate-fade-slide-down">
            <h1 className="text-3xl font-bold mb-2">Attachments</h1>
            <p className="text-zinc-400">
              Manage extended content storage for your memories (up to 100MB per attachment)
            </p>
          </div>

          <div className="grid gap-6 animate-fade-slide-down delay-1">
            {/* Create Section */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="text-xl font-semibold mb-4">Create New Attachment</h2>
              <Button
                onClick={handleCreate}
                className="bg-primary hover:bg-primary/90 text-white"
              >
                <GoPlus className="mr-2" />
                Create Attachment
              </Button>
            </div>

            {/* Search Section */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="text-xl font-semibold mb-4">Search by ID</h2>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="search-id">Attachment ID</Label>
                  <div className="flex gap-2">
                    <Input
                      id="search-id"
                      value={searchId}
                      onChange={(e) => setSearchId(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleSearch();
                        }
                      }}
                      placeholder="Enter UUID or custom ID"
                      className="bg-zinc-950 border-zinc-800 font-mono"
                    />
                    <Button onClick={handleSearch}>
                      <Search className="w-4 h-4 mr-2" />
                      Search
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Info Section */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="text-xl font-semibold mb-4">About Attachments</h2>
              <div className="space-y-3 text-sm text-zinc-400">
                <p>
                  <strong className="text-zinc-300">What are attachments?</strong> Attachments allow you to store extended text content (up to 100MB) that can be linked to memory entries.
                </p>
                <p>
                  <strong className="text-zinc-300">How to use:</strong> Create an attachment to get its ID, then reference this ID when creating memories with extended content.
                </p>
                <p>
                  <strong className="text-zinc-300">API Access:</strong> Attachments are available via REST API at <code className="bg-zinc-950 px-1 py-0.5 rounded">/api/v1/attachments</code>
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
