
import { Link } from "@tanstack/react-router";

interface StudentLinkProps {
    studentTz: string;
    studentName: string;
    className?: string;
}

export function StudentLink({ studentTz, studentName, className }: StudentLinkProps) {
    return (
        <Link
            to="/students/$studentTz"
            params={{ studentTz }}
            className={`hover:text-primary hover:underline ${className || ""}`}
        >
            {studentName}
        </Link>
    );
}
