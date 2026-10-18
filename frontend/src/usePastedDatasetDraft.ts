import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
} from "react";

import {
  parsePastedTablePreview,
  spreadsheetColumnLabel,
  utf8ByteCount,
  type PastedTablePreview,
} from "./pastedTablePreview";

export type PastedDatasetDraftMode = "grid" | "raw";
export type PastedDatasetDraftChangeReason = "user" | "reset";

export interface PastedCellSelection {
  address: string;
  columnIndex: number;
  rowIndex: number;
  value: string;
}

export interface PastedDatasetDraft {
  byteCount: number;
  canSubmit: boolean;
  characterCount: number;
  hasHeaderPreview: boolean;
  mode: PastedDatasetDraftMode;
  pasteSurfaceRef: React.RefObject<HTMLDivElement>;
  preview: PastedTablePreview | null;
  rawTextAreaRef: React.RefObject<HTMLTextAreaElement>;
  selection: PastedCellSelection | null;
  clear: (expectedRevision?: number, reason?: PastedDatasetDraftChangeReason) => void;
  getRevision: () => number;
  getRawText: () => string;
  onCellSelect: (rowIndex: number, columnIndex: number) => void;
  onDirectPaste: (event: ClipboardEvent<HTMLElement>) => void;
  onRawTextChange: (event: ChangeEvent<HTMLTextAreaElement>) => void;
  replace: () => void;
  setHasHeaderPreview: (value: boolean) => void;
  setMode: (mode: PastedDatasetDraftMode) => void;
}

export function usePastedDatasetDraft(onDraftChange?: (dirty: boolean, reason: PastedDatasetDraftChangeReason) => void): PastedDatasetDraft {
  const rawTextRef = useRef("");
  const revisionRef = useRef(0);
  const onDraftChangeRef = useRef(onDraftChange);
  onDraftChangeRef.current = onDraftChange;
  const rawTextAreaRef = useRef<HTMLTextAreaElement>(null);
  const pasteSurfaceRef = useRef<HTMLDivElement>(null);
  const [characterCount, setCharacterCount] = useState(0);
  const [byteCount, setByteCount] = useState(0);
  const [hasNonWhitespace, setHasNonWhitespace] = useState(false);
  const [preview, setPreview] = useState<PastedTablePreview | null>(null);
  const [mode, setModeState] = useState<PastedDatasetDraftMode>("grid");
  const [hasHeaderPreview, setHasHeaderPreview] = useState(true);
  const [selectedCoordinates, setSelectedCoordinates] = useState<{
    rowIndex: number;
    columnIndex: number;
  } | null>(null);

  const setRawText = useCallback((text: string) => {
    revisionRef.current += 1;
    rawTextRef.current = text;
    onDraftChangeRef.current?.(text.length > 0, "user");
    if (rawTextAreaRef.current !== null && rawTextAreaRef.current.value !== text) {
      rawTextAreaRef.current.value = text;
    }
    setCharacterCount(text.length);
    setByteCount(utf8ByteCount(text));
    setHasNonWhitespace(text.trim().length > 0);
    const nextPreview = parsePastedTablePreview(text);
    setPreview(nextPreview);
    setSelectedCoordinates(null);
    setModeState(nextPreview.rawModeOnly ? "raw" : "grid");
  }, []);

  const clear = useCallback((expectedRevision?: number, reason: PastedDatasetDraftChangeReason = "user") => {
    if (expectedRevision !== undefined && expectedRevision !== revisionRef.current) return;
    revisionRef.current += 1;
    rawTextRef.current = "";
    onDraftChangeRef.current?.(false, reason);
    if (rawTextAreaRef.current !== null) rawTextAreaRef.current.value = "";
    setCharacterCount(0);
    setByteCount(0);
    setHasNonWhitespace(false);
    setPreview(null);
    setSelectedCoordinates(null);
    setModeState("grid");
    setHasHeaderPreview(true);
  }, []);

  const selection = useMemo<PastedCellSelection | null>(() => {
    if (preview === null || selectedCoordinates === null) return null;
    const value = preview.rows[selectedCoordinates.rowIndex]?.[selectedCoordinates.columnIndex];
    if (value === undefined) return null;
    return {
      address: `${spreadsheetColumnLabel(selectedCoordinates.columnIndex)}${selectedCoordinates.rowIndex + 1}`,
      columnIndex: selectedCoordinates.columnIndex,
      rowIndex: selectedCoordinates.rowIndex,
      value,
    };
  }, [preview, selectedCoordinates]);

  return {
    byteCount,
    canSubmit: hasNonWhitespace,
    characterCount,
    hasHeaderPreview,
    mode,
    pasteSurfaceRef,
    preview,
    rawTextAreaRef,
    selection,
    clear,
    getRevision: () => revisionRef.current,
    getRawText: () => rawTextRef.current,
    onCellSelect: (rowIndex, columnIndex) => {
      setSelectedCoordinates({ rowIndex, columnIndex });
    },
    onDirectPaste: (event) => {
      const text = event.clipboardData.getData("text/plain");
      event.preventDefault();
      setRawText(text);
    },
    onRawTextChange: (event) => {
      setRawText(event.currentTarget.value);
    },
    replace: () => {
      clear();
      globalThis.setTimeout(() => pasteSurfaceRef.current?.focus(), 0);
    },
    setHasHeaderPreview: (value) => {
      revisionRef.current += 1;
      setHasHeaderPreview(value);
      onDraftChangeRef.current?.(rawTextRef.current.length > 0, "user");
    },
    setMode: (nextMode) => {
      if (nextMode === "grid" && preview?.rawModeOnly) return;
      setModeState(nextMode);
    },
  };
}
