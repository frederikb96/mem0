"use client";

import { SortAsc, SortDesc, ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuGroup,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";

const sortColumns = [
  { label: "Created At", value: "created_at" },
  { label: "Updated At", value: "updated_at" },
];

export function AttachmentSort() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentSortColumn = searchParams.get("sort_column") || "created_at";
  const currentSortDirection = (searchParams.get("sort_direction") as "asc" | "desc") || "desc";

  const handleSortChange = (column: string) => {
    const params = new URLSearchParams(searchParams.toString());

    // Toggle direction if clicking the same column, otherwise default to desc
    const newDirection =
      currentSortColumn === column && currentSortDirection === "asc"
        ? "desc"
        : "asc";

    params.set("sort_column", column);
    params.set("sort_direction", newDirection);
    params.set("page", "1"); // Reset to first page when sorting changes

    router.push(`/attachments?${params.toString()}`);
  };

  const currentColumnLabel = sortColumns.find((c) => c.value === currentSortColumn)?.label || "Created At";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="h-9 px-4 border-zinc-700/50 bg-zinc-900 hover:bg-zinc-800"
        >
          {currentSortDirection === "asc" ? (
            <SortAsc className="h-4 w-4" />
          ) : (
            <SortDesc className="h-4 w-4" />
          )}
          Sort: {currentColumnLabel}
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56 bg-zinc-900 border-zinc-800 text-zinc-100">
        <DropdownMenuLabel>Sort by</DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-zinc-800" />
        <DropdownMenuGroup>
          {sortColumns.map((column) => (
            <DropdownMenuItem
              key={column.value}
              onClick={() => handleSortChange(column.value)}
              className="cursor-pointer flex justify-between items-center"
            >
              {column.label}
              {currentSortColumn === column.value &&
                (currentSortDirection === "asc" ? (
                  <SortAsc className="h-4 w-4 text-primary" />
                ) : (
                  <SortDesc className="h-4 w-4 text-primary" />
                ))}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
