// src/components/DropZone.tsx
import React, { useRef, useState } from "react";

type Props = {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
};

export default function DropZone({ onFiles, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const pickFiles = () => {
    if (!disabled) inputRef.current?.click();
  };

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length) {
      onFiles(Array.from(e.target.files));
      e.target.value = ""; // reset
    }
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      onFiles(Array.from(e.dataTransfer.files));
    }
  };

  return (
    <div
      role="button"
      onClick={pickFiles}
      onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      style={{
        cursor: disabled ? "not-allowed" : "pointer",
        borderRadius: 12,
        border: "2px dashed #c9d1e6",
        background: dragOver ? "#f6f9ff" : "#fafbff",
        padding: 32,
        textAlign: "center",
        color: "#3a4861",
      }}
    >
      <div style={{ fontSize: 48, lineHeight: "48px", opacity: 0.6 }}>☁️</div>
      <div style={{ marginTop: 8 }}>
        <span style={{ color: "#2563eb", textDecoration: "underline" }}>Choose files</span>
        <span> or drag & drop</span>
      </div>
      <div style={{ marginTop: 6, fontSize: 12, color: "#6b7280" }}>
        Supported: PDF • Max 10MB each • up to 10 files
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        onChange={onChange}
        style={{ display: "none" }}
      />
    </div>
  );
}
