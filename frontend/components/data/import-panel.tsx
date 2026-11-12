"use client";

import { useState } from "react";
import { toast } from "sonner";

import { ImportPreviewTable } from "@/components/data/import-preview-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { downloadUrl } from "@/lib/api";
import { usePreviewExcel, usePreviewRawText } from "@/lib/queries/imports";
import type { ImportPreviewResponse } from "@/lib/types";

export function ImportPanel({ vehicleId }: { vehicleId: number | undefined }) {
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [text, setText] = useState("");
  const [startYear, setStartYear] = useState(String(new Date().getFullYear()));

  const previewExcel = usePreviewExcel(vehicleId);
  const previewRawText = usePreviewRawText(vehicleId);

  const handleExcelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    previewExcel.mutate(file, {
      onSuccess: setPreview,
      onError: () => toast.error("Couldn't read that file"),
    });
    e.target.value = "";
  };

  const handleRawTextPreview = () => {
    previewRawText.mutate(
      { text, start_year: Number(startYear) },
      { onSuccess: setPreview, onError: () => toast.error("Couldn't parse that text") },
    );
  };

  if (preview) {
    return (
      <div className="space-y-3">
        <ImportPreviewTable
          vehicleId={vehicleId}
          initialRows={preview.rows}
          onCommitted={() => {
            setPreview(null);
            setText("");
          }}
        />
        <Button variant="ghost" onClick={() => setPreview(null)}>
          Start over
        </Button>
      </div>
    );
  }

  return (
    <Tabs defaultValue="excel">
      <TabsList className="w-full">
        <TabsTrigger value="excel" className="flex-1">
          Excel
        </TabsTrigger>
        <TabsTrigger value="text" className="flex-1">
          Paste notes
        </TabsTrigger>
      </TabsList>

      <TabsContent value="excel" className="mt-4 space-y-3">
        <a
          href={vehicleId ? downloadUrl(`/api/vehicles/${vehicleId}/import/template.xlsx`) : "#"}
          className="text-sm underline underline-offset-4"
        >
          Download the import template
        </a>
        <Input
          type="file"
          accept=".xlsx"
          onChange={handleExcelChange}
          disabled={previewExcel.isPending}
        />
      </TabsContent>

      <TabsContent value="text" className="mt-4 space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="start-year">Starting year of these notes</Label>
          <Input
            id="start-year"
            type="number"
            className="w-28"
            value={startYear}
            onChange={(e) => setStartYear(e.target.value)}
          />
        </div>
        <Textarea
          rows={8}
          placeholder={"12.50 lt - 1000rs - 3767 - 08/06 - full tank - ngp"}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button
          onClick={handleRawTextPreview}
          disabled={!text.trim() || previewRawText.isPending}
        >
          {previewRawText.isPending ? "Parsing…" : "Preview"}
        </Button>
      </TabsContent>
    </Tabs>
  );
}
