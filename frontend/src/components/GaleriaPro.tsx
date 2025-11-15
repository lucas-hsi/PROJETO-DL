import React, { useEffect, useMemo, useRef, useState } from "react";
import styled from "styled-components";
import { colors, shadows, radius } from "@/styles/tokens";

type GaleriaProProps = {
  imagens: string[];
};

const PLACEHOLDER = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHZpZXdCb3g9IjAgMCA0OCA0OCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjQ4IiBoZWlnaHQ9IjQ4IiByeD0iOCIgZmlsbD0iI0Y5RkFGQiIvPgo8cGF0aCBkPSJNMTYgMTZWMzJIMzJWMTZIMTZaIiBzdHJva2U9IiM5Q0EzQUYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+CjxwYXRoIGQ9Ik0yMCAxNlYyMEgyNFYxNkgyMFoiIGZpbGw9IiM5Q0EzQUYiLz4KPC9zdmc+";

const Wrap = styled.div`
  position: relative;
  width: 48px;
  height: 48px;
`;

const Main = styled.div`
  width: 100%;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #f1f5f9;
`;

const MainImg = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: zoom-in;
`;

const ThumbBar = styled.div`
  position: absolute;
  left: 2px;
  right: 2px;
  bottom: 2px;
  display: inline-flex;
  gap: 4px;
  padding: 2px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(2px);
  border-radius: 8px;
  overflow-x: auto;
  max-width: 44px;
`;

const ThumbMini = styled.img`
  width: 12px;
  height: 12px;
  border-radius: 4px;
  object-fit: cover;
  flex: 0 0 auto;
  cursor: pointer;
  border: 1px solid rgba(0,0,0,0.05);
`;

const ModalOverlay = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  position: relative;
  width: 90vw;
  height: 90vh;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${colors.card};
  border-radius: ${radius.md};
  box-shadow: ${shadows.hover};
  overflow: hidden;
`;

const ModalImg = styled.img<{ $scale?: number }>`
  user-select: none;
  max-width: 100%;
  max-height: 100%;
  transform: scale(${(p) => p.$scale || 1});
  transform-origin: center center;
`;

const Controls = styled.div`
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  gap: 12px;
`;

const CtrlBtn = styled.button`
  padding: 8px 12px;
  border-radius: 9999px;
  border: 1px solid ${colors.border};
  background: ${colors.white};
  color: ${colors.textDark};
  font-weight: 500;
`;

export default function GaleriaPro({ imagens }: GaleriaProProps) {
  const lista = useMemo(() => (Array.isArray(imagens) ? imagens.filter(Boolean) : []), [imagens]);
  const [idx, setIdx] = useState(0);
  const [open, setOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const modalRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "ArrowRight") setIdx((v) => (v + 1) % Math.max(lista.length || 1, 1));
      if (e.key === "ArrowLeft") setIdx((v) => (v - 1 + Math.max(lista.length || 1, 1)) % Math.max(lista.length || 1, 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, lista.length]);

  useEffect(() => {
    setScale(1);
  }, [idx, open]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((s) => Math.min(4, Math.max(1, s + delta)));
  };

  const onErrorImg = (ev: React.SyntheticEvent<HTMLImageElement>) => {
    (ev.target as HTMLImageElement).src = PLACEHOLDER;
  };

  const current = lista[idx] || PLACEHOLDER;

  return (
    <Wrap>
      <Main onClick={() => setOpen(true)}>
        <MainImg src={current} alt="Imagem do produto" onError={onErrorImg} />
      </Main>
      {lista.length > 0 && (
        <ThumbBar>
          {lista.map((src, i) => (
            <ThumbMini key={`mini-${i}`} src={src} alt="mini" onError={onErrorImg} onClick={(e) => { e.stopPropagation(); setIdx(i); }} />
          ))}
        </ThumbBar>
      )}
      {open && (
        <ModalOverlay onClick={() => setOpen(false)}>
          <ModalContent ref={modalRef} onClick={(e) => e.stopPropagation()} onWheel={onWheel}>
            <ModalImg src={current} alt="Imagem" onError={onErrorImg} $scale={scale} />
            <Controls>
              <CtrlBtn onClick={() => setIdx((v) => (v - 1 + Math.max(lista.length || 1, 1)) % Math.max(lista.length || 1, 1))}>anterior</CtrlBtn>
              <CtrlBtn onClick={() => setIdx((v) => (v + 1) % Math.max(lista.length || 1, 1))}>próximo</CtrlBtn>
              <CtrlBtn onClick={() => setOpen(false)}>fechar</CtrlBtn>
            </Controls>
          </ModalContent>
        </ModalOverlay>
      )}
    </Wrap>
  );
}