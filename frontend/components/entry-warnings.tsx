"use client";

import { AlertTriangle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { SuggestedFix, ValidationWarning } from "@/lib/types";

export function EntryWarnings({
  warnings,
  onFix,
}: {
  warnings: ValidationWarning[];
  onFix: (action: SuggestedFix["action"], fix: SuggestedFix) => void;
}) {
  if (warnings.length === 0) return null;

  return (
    <div className="space-y-2">
      {warnings.map((warning) => (
        <Alert key={warning.code} variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle className="capitalize">{warning.code.replaceAll("_", " ")}</AlertTitle>
          <AlertDescription>
            <p>{warning.message}</p>
            {warning.suggested_fixes.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {warning.suggested_fixes.map((fix) => (
                  <Button
                    key={fix.action}
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => onFix(fix.action, fix)}
                  >
                    {fix.label}
                  </Button>
                ))}
              </div>
            )}
          </AlertDescription>
        </Alert>
      ))}
    </div>
  );
}
