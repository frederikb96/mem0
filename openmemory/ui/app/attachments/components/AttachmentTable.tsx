"use client";

import {
  Edit,
  MoreHorizontal,
  Trash2,
  Eye,
  Copy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { useAttachmentsApi } from "@/hooks/useAttachmentsApi";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/store/store";
import {
  selectAttachment,
  deselectAttachment,
  selectAllAttachments,
  clearSelection,
} from "@/store/attachmentsSlice";
import { formatDate } from "@/lib/helpers";
import { useState } from "react";
import { AttachmentDialog } from "./AttachmentDialog";

export function AttachmentTable() {
  const { toast } = useToast();
  const dispatch = useDispatch();
  const selectedAttachmentIds = useSelector(
    (state: RootState) => state.attachments.selectedAttachmentIds
  );
  const attachments = useSelector((state: RootState) => state.attachments.attachments);

  const { deleteAttachment, isLoading } = useAttachmentsApi();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"view" | "edit" | "create">("view");
  const [viewingId, setViewingId] = useState<string | undefined>(undefined);

  const handleDeleteAttachment = async (id: string) => {
    if (!confirm("Are you sure you want to delete this attachment?")) return;

    try {
      await deleteAttachment(id);
      toast({
        title: "Success",
        description: "Attachment deleted successfully",
      });
      // Trigger refresh by updating URL
      window.location.reload();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete attachment",
        variant: "destructive",
      });
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      dispatch(selectAllAttachments());
    } else {
      dispatch(clearSelection());
    }
  };

  const handleSelectAttachment = (id: string, checked: boolean) => {
    if (checked) {
      dispatch(selectAttachment(id));
    } else {
      dispatch(deselectAttachment(id));
    }
  };

  const handleViewAttachment = (id: string) => {
    setViewingId(id);
    setDialogMode("view");
    setDialogOpen(true);
  };

  const handleEditAttachment = (id: string) => {
    setViewingId(id);
    setDialogMode("edit");
    setDialogOpen(true);
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    toast({
      title: "Copied",
      description: "Attachment ID copied to clipboard",
    });
  };

  const isAllSelected =
    attachments.length > 0 && selectedAttachmentIds.length === attachments.length;
  const isPartiallySelected =
    selectedAttachmentIds.length > 0 && selectedAttachmentIds.length < attachments.length;

  return (
    <>
      <AttachmentDialog
        attachmentId={viewingId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
      />
      <div className="rounded-md border">
        <Table className="">
          <TableHeader>
            <TableRow className="bg-zinc-800 hover:bg-zinc-800">
              <TableHead className="w-[50px] pl-4">
                <Checkbox
                  className="data-[state=checked]:border-primary border-zinc-500/50"
                  checked={isAllSelected}
                  data-state={
                    isPartiallySelected
                      ? "indeterminate"
                      : isAllSelected
                      ? "checked"
                      : "unchecked"
                  }
                  onCheckedChange={handleSelectAll}
                />
              </TableHead>
              <TableHead className="border-zinc-700 w-[200px]">
                ID
              </TableHead>
              <TableHead className="border-zinc-700 min-w-[300px]">
                Content Preview
              </TableHead>
              <TableHead className="border-zinc-700 w-[120px]">
                Size
              </TableHead>
              <TableHead className="w-[140px] border-zinc-700">
                Created
              </TableHead>
              <TableHead className="w-[140px] border-zinc-700">
                Updated
              </TableHead>
              <TableHead className="text-right border-zinc-700 flex justify-center">
                <div className="flex items-center justify-end">
                  <MoreHorizontal className="h-4 w-4 mr-2" />
                </div>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {attachments.map((attachment) => (
              <TableRow
                key={attachment.id}
                className={`hover:bg-zinc-900/50 ${isLoading ? "animate-pulse opacity-50" : ""}`}
              >
                <TableCell className="pl-4">
                  <Checkbox
                    className="data-[state=checked]:border-primary border-zinc-500/50"
                    checked={selectedAttachmentIds.includes(attachment.id)}
                    onCheckedChange={(checked) =>
                      handleSelectAttachment(attachment.id, checked as boolean)
                    }
                  />
                </TableCell>
                <TableCell className="font-mono text-xs text-zinc-400">
                  <div className="flex items-center gap-1">
                    <span className="truncate max-w-[150px]">
                      {attachment.id.substring(0, 8)}...
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => handleCopyId(attachment.id)}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
                <TableCell
                  onClick={() => handleViewAttachment(attachment.id)}
                  className="cursor-pointer hover:text-white"
                >
                  <div className="max-w-[400px] truncate">
                    {attachment.content}
                  </div>
                </TableCell>
                <TableCell className="text-center text-zinc-400">
                  {(attachment.content_length / 1024).toFixed(1)} KB
                </TableCell>
                <TableCell className="text-center text-zinc-400">
                  {formatDate(attachment.created_at)}
                </TableCell>
                <TableCell className="text-center text-zinc-400">
                  {formatDate(attachment.updated_at)}
                </TableCell>
                <TableCell className="text-right flex justify-center">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      className="bg-zinc-900 border-zinc-800"
                    >
                      <DropdownMenuItem
                        className="cursor-pointer"
                        onClick={() => handleViewAttachment(attachment.id)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="cursor-pointer"
                        onClick={() => handleEditAttachment(attachment.id)}
                      >
                        <Edit className="mr-2 h-4 w-4" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="cursor-pointer text-red-500 focus:text-red-500"
                        onClick={() => handleDeleteAttachment(attachment.id)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
