"use client";

import { useEffect, useState } from "react";
import { AttachmentsSection } from "./components/AttachmentsSection";
import { AttachmentFilters } from "./components/AttachmentFilters";
import { useRouter, useSearchParams } from "next/navigation";
import { AttachmentDialog } from "./components/AttachmentDialog";
import "@/styles/animation.css";

export default function AttachmentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [autoOpenId, setAutoOpenId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    // Set default pagination values if not present in URL
    if (!searchParams.has("page") || !searchParams.has("size")) {
      const params = new URLSearchParams(searchParams.toString());
      if (!searchParams.has("page")) params.set("page", "1");
      if (!searchParams.has("size")) params.set("size", "10");
      router.push(`/attachments?${params.toString()}`);
    }

    // Check if we should auto-open an attachment (from memory link)
    const attachmentId = searchParams.get("id");
    if (attachmentId) {
      setAutoOpenId(attachmentId);
      setDialogOpen(true);

      // Remove the 'id' parameter from URL to clean it up
      const params = new URLSearchParams(searchParams.toString());
      params.delete("id");
      router.replace(`/attachments?${params.toString()}`);
    }
  }, [router, searchParams]);

  return (
    <>
      <AttachmentDialog
        attachmentId={autoOpenId || undefined}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode="view"
      />
      <div className="">
        <main className="flex-1 py-6">
          <div className="container">
            <div className="mb-8 animate-fade-slide-down">
              <h1 className="text-3xl font-bold mb-2">Attachments</h1>
              <p className="text-zinc-400">
                Manage extended content storage for your memories (up to 100MB per attachment)
              </p>
            </div>
            <div className="mt-1 pb-4 animate-fade-slide-down delay-1">
              <AttachmentFilters />
            </div>
            <div className="animate-fade-slide-down delay-2">
              <AttachmentsSection />
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
