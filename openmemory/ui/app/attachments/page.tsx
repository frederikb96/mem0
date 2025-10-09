"use client";

import { useEffect } from "react";
import { AttachmentsSection } from "./components/AttachmentsSection";
import { AttachmentFilters } from "./components/AttachmentFilters";
import { useRouter, useSearchParams } from "next/navigation";
import "@/styles/animation.css";

export default function AttachmentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Set default pagination values if not present in URL
    if (!searchParams.has("page") || !searchParams.has("size")) {
      const params = new URLSearchParams(searchParams.toString());
      if (!searchParams.has("page")) params.set("page", "1");
      if (!searchParams.has("size")) params.set("size", "10");
      router.push(`/attachments?${params.toString()}`);
    }
  }, [router, searchParams]);

  return (
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
  );
}
