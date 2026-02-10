import { useTranslation } from "react-i18next";
import {
    Pagination,
    PaginationContent,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
    PaginationEllipsis,
} from "@/components/ui/pagination";

interface TablePaginationProps {
    page: number;
    totalPages: number;
    onPageChange: (page: number) => void;
}

export function TablePagination({ page, totalPages, onPageChange }: TablePaginationProps) {
    const { t } = useTranslation();

    if (totalPages <= 1) return null;

    const getPageNumbers = () => {
        const pages: (number | "ellipsis")[] = [];
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            pages.push(1);
            if (page > 3) pages.push("ellipsis");
            for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
                pages.push(i);
            }
            if (page < totalPages - 2) pages.push("ellipsis");
            pages.push(totalPages);
        }
        return pages;
    };

    const isPrevDisabled = page <= 1;
    const isNextDisabled = page >= totalPages;

    return (
        <div className="p-4 border-t">
            <Pagination>
                <PaginationContent>
                    <PaginationItem>
                        <PaginationPrevious
                            onClick={() => !isPrevDisabled && onPageChange(page - 1)}
                            className={isPrevDisabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
                            aria-disabled={isPrevDisabled}
                            tabIndex={isPrevDisabled ? -1 : undefined}
                        >
                            {t("pagination.previous")}
                        </PaginationPrevious>
                    </PaginationItem>
                    {getPageNumbers().map((p, i) =>
                        p === "ellipsis" ? (
                            <PaginationItem key={`ellipsis-${i}`}>
                                <PaginationEllipsis />
                            </PaginationItem>
                        ) : (
                            <PaginationItem key={p}>
                                <PaginationLink
                                    isActive={p === page}
                                    onClick={() => onPageChange(p)}
                                    className="cursor-pointer"
                                >
                                    {p}
                                </PaginationLink>
                            </PaginationItem>
                        )
                    )}
                    <PaginationItem>
                        <PaginationNext
                            onClick={() => !isNextDisabled && onPageChange(page + 1)}
                            className={isNextDisabled ? "pointer-events-none opacity-50" : "cursor-pointer"}
                            aria-disabled={isNextDisabled}
                            tabIndex={isNextDisabled ? -1 : undefined}
                        >
                            {t("pagination.next")}
                        </PaginationNext>
                    </PaginationItem>
                </PaginationContent>
            </Pagination>
        </div>
    );
}
