"use client";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { Eraser, PenLine, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface SignatureCanvasProps {
  width?: number;
  height?: number;
  strokeColor?: string;
  strokeWidth?: number;
  className?: string;
  onChange?: (dataUrl: string | null) => void;
  disabled?: boolean;
}

export function SignatureCanvas({
  width = 480,
  height = 180,
  strokeColor = "#2dd4bf",
  strokeWidth = 2,
  className,
  onChange,
  disabled = false,
}: SignatureCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasStroke, setHasStroke] = useState(false);

  const getContext = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = strokeWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    return ctx;
  }, [strokeColor, strokeWidth]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = getContext();
    if (!canvas || !ctx) return;
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = strokeColor;
  }, [getContext, height, strokeColor, width]);

  const emitChange = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    onChange?.(hasStroke ? canvas.toDataURL("image/png") : null);
  }, [hasStroke, onChange]);

  function pointerPosition(e: React.PointerEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * width,
      y: ((e.clientY - rect.top) / rect.height) * height,
    };
  }

  function handlePointerDown(e: React.PointerEvent<HTMLCanvasElement>) {
    if (disabled) return;
    const ctx = getContext();
    if (!ctx) return;
    const { x, y } = pointerPosition(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
    canvasRef.current?.setPointerCapture(e.pointerId);
  }

  function handlePointerMove(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!isDrawing || disabled) return;
    const ctx = getContext();
    if (!ctx) return;
    const { x, y } = pointerPosition(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasStroke(true);
  }

  function handlePointerUp(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!isDrawing) return;
    setIsDrawing(false);
    canvasRef.current?.releasePointerCapture(e.pointerId);
    emitChange();
  }

  function clearCanvas() {
    const canvas = canvasRef.current;
    const ctx = getContext();
    if (!canvas || !ctx) return;
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, width, height);
    setHasStroke(false);
    onChange?.(null);
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="relative overflow-hidden rounded-lg border border-vault-700 bg-vault-950">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className={cn(
            "w-full touch-none",
            disabled ? "cursor-not-allowed opacity-50" : "cursor-crosshair",
          )}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        />
        {!hasStroke && !disabled && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <p className="flex items-center gap-2 text-sm text-slate-600">
              <PenLine className="h-4 w-4" />
              Sign here
            </p>
          </div>
        )}
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={clearCanvas} disabled={disabled || !hasStroke}>
          <RotateCcw className="h-3.5 w-3.5" />
          Clear
        </Button>
        <Button variant="ghost" size="sm" onClick={clearCanvas} disabled={disabled}>
          <Eraser className="h-3.5 w-3.5" />
          Reset pad
        </Button>
      </div>
    </div>
  );
}
