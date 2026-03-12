import { useState, useCallback } from "react";
import { Upload } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
}

export function DropZone({ onFiles }: DropZoneProps) {
  const { t } = useTranslation("upload");
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.length)
        onFiles(Array.from(e.dataTransfer.files));
    },
    [onFiles],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.length) {
        onFiles(Array.from(e.target.files));
        e.target.value = "";
      }
    },
    [onFiles],
  );

  return (
    <Card
      className={`border-2 border-dashed transition-colors ${
        dragActive
          ? "border-primary bg-primary/5"
          : "border-border hover:border-primary/50"
      }`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <CardContent className="p-6">
        <div className="flex flex-col items-center text-center py-6">
          <Upload className="size-10 text-muted-foreground mb-3" />
          <p className="text-base font-medium mb-1">{t("dropzone.dragHere")}</p>
          <p className="text-sm text-muted-foreground mb-3">
            {t("dropzone.orClick")}
          </p>
          <Input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
            multiple
          />
          <Label htmlFor="file-upload" className="cursor-pointer">
            <Button asChild size="sm">
              <span>{t("dropzone.button")}</span>
            </Button>
          </Label>
        </div>
      </CardContent>
    </Card>
  );
}
