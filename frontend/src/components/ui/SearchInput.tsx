import React, { useEffect, useMemo, useRef, useState } from 'react';
import styled from 'styled-components';
import { Search, X } from 'lucide-react';
import { colors, radius, shadows } from '@/styles/tokens';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
}

const Wrapper = styled.div`
  position: relative;
  width: 100%;
  max-width: 420px;
`;

const Field = styled.input`
  width: 100%;
  padding: 12px 40px 12px 40px;
  border: 1px solid ${colors.border};
  border-radius: 12px;
  background: ${colors.card};
  color: ${colors.textDark};
  box-shadow: ${shadows.base};
  transition: all 0.2s ease;
  
  &::placeholder { color: ${colors.textLight}; }
  &:focus {
    outline: none;
    border-color: #5B2EFF;
    box-shadow: 0 0 0 3px rgba(91, 46, 255, 0.1);
  }
`;

const IconLeft = styled.div`
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: ${colors.textLight};
`;

const ClearBtn = styled.button`
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: ${colors.textLight};
  border-radius: ${radius.sm};
  padding: 4px;
  cursor: pointer;
  &:hover { color: ${colors.textDark}; }
`;

export default function SearchInput({ value, onChange, placeholder = 'Buscar', debounceMs = 250 }: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => onChange(localValue), debounceMs);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [localValue, debounceMs, onChange]);

  return (
    <Wrapper>
      <IconLeft>
        <Search size={20} />
      </IconLeft>
      <Field
        type="text"
        placeholder={placeholder}
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
      />
      {localValue && (
        <ClearBtn onClick={() => setLocalValue('')} aria-label="Limpar busca">
          <X size={18} />
        </ClearBtn>
      )}
    </Wrapper>
  );
}