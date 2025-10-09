"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AttachmentTable } from "./AttachmentTable";
import { useAttachmentsApi } from "@/hooks/useAttachmentsApi";
import { useRouter, useSearchParams } from "next/navigation";
import { AttachmentDialog } from "./AttachmentDialog";
import { MemoryPagination } from "@/app/memories/components/MemoryPagination";
import { PageSizeSelector } from "@/app/memories/components/PageSizeSelector";

// Simple skeleton for loading state
function AttachmentTableSkeleton() {
  return (
    <div className="rounded-md border border-zinc-800 p-4">
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-zinc-800 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
}

export function AttachmentsSection() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { fetchAttachments } = useAttachmentsApi();
  const [attachments, setAttachments] = useState<any[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);

  const currentPage = Number(searchParams.get("page")) || 1;
  const itemsPerPage = Number(searchParams.get("size")) || 10;
  const searchQuery = searchParams.get("search") || "";
  const sortColumn = searchParams.get("sort_column") || "created_at";
  const sortDirection = (searchParams.get("sort_direction") as "asc" | "desc") || "desc";

  useEffect(() => {
    const loadAttachments = async () => {
      setIsLoading(true);
      try {
        const result = await fetchAttachments(
          searchQuery,
          currentPage,
          itemsPerPage,
          sortColumn,
          sortDirection
        );
        setAttachments(result.attachments);
        setTotalItems(result.total);
        setTotalPages(result.pages);
      } catch (error) {
        console.error("Failed to fetch attachments:", error);
      }
      setIsLoading(false);
    };

    loadAttachments();
  }, [currentPage, itemsPerPage, searchQuery, sortColumn, sortDirection, fetchAttachments]);

  const setCurrentPage = (page: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", page.toString());
    params.set("size", itemsPerPage.toString());
    router.push(`/attachments?${params.toString()}`);
  };

  const handlePageSizeChange = (size: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", "1"); // Reset to page 1 when changing page size
    params.set("size", size.toString());
    router.push(`/attachments?${params.toString()}`);
  };

  const handleCreate = () => {
    setDialogOpen(true);
  };

  if (isLoading) {
    return (
      <div className="w-full bg-transparent">
        <AttachmentTableSkeleton />
        <div className="flex items-center justify-between mt-4">
          <div className="h-8 w-32 bg-zinc-800 rounded animate-pulse" />
          <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse" />
          <div className="h-8 w-32 bg-zinc-800 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <>
      <AttachmentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode="create"
        attachmentId={undefined}
      />
      <div className="w-full bg-transparent">
        <div>
          {attachments.length > 0 ? (
            <>
              <AttachmentTable />
              <div className="flex items-center justify-between mt-4">
                <PageSizeSelector
                  pageSize={itemsPerPage}
                  onPageSizeChange={handlePageSizeChange}
                />
                <div className="text-sm text-zinc-500 mr-2">
                  Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                  {Math.min(currentPage * itemsPerPage, totalItems)} of{" "}
                  {totalItems} attachments
                </div>
                <MemoryPagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  setCurrentPage={setCurrentPage}
                />
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="rounded-full bg-zinc-800 p-3 mb-4">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-6 w-6 text-zinc-400"
                >
                  <path d="M21 9v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7"></path>
                  <path d="M16 2v6h6"></path>
                  <path d="M12 18v-6"></path>
                  <path d="M9 15h6"></path>
                </svg>
              </div>
              <h3 className="text-lg font-medium">No attachments found</h3>
              <p className="text-zinc-400 mt-1 mb-4">
                {searchQuery
                  ? "Try adjusting your search"
                  : "Create your first attachment to see it here"}
              </p>
              <Button onClick={handleCreate}>Create Attachment</Button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
