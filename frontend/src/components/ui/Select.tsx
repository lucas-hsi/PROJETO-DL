import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import styled from 'styled-components';
import { colors, radius, typography } from '@/styles/tokens';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  className?: string;
}

const Label = styled.label`
  display: block;
  font-size: 12px;
  font-weight: ${typography.weightMedium};
  color: ${colors.textDark};
  margin-bottom: 8px;
`;

const Wrapper = styled.div`
  width: 100%;
`;

const Trigger = styled.button<{ $error?: boolean }>`
  width: 100%;
  border-radius: ${radius.md};
  border: 1px solid ${colors.border};
  background: ${colors.card};
  backdrop-filter: blur(14px);
  padding: 12px 40px 12px 16px;
  text-align: left;
  color: ${colors.textDark};
  position: relative;
  transition: all 0.2s ease;
  &:focus { border-color: ${colors.primary}; box-shadow: 0 0 0 3px rgba(79,70,229,0.2); }
  ${({ $error }) => ($error ? `border-color: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.2);` : '')}
`;

const Chevron = styled.span`
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: ${colors.textLight};
`;

const Options = styled(motion.ul)`
  position: absolute;
  z-index: 10;
  margin-top: 4px;
  width: 100%;
  max-height: 240px;
  overflow: auto;
  border-radius: ${radius.md};
  border: 1px solid ${colors.border};
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(14px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
`;

const Option = styled.li<{ $active?: boolean }>`
  cursor: pointer;
  padding: 12px 36px 12px 16px;
  color: ${colors.textDark};
  ${({ $active }) => ($active ? `background: rgba(99,102,241,0.1); color: ${colors.primary}; font-weight: ${typography.weightMedium};` : '')}
`;

export const Select: React.FC<SelectProps> = ({ options, value, onChange, placeholder = 'Selecione uma opção', label, error }) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(o => o.value === value);

  return (
    <Wrapper>
      {label && <Label>{label}</Label>}
      <div style={{ position: 'relative' }}>
        <Trigger type="button" onClick={() => setIsOpen(!isOpen)} $error={!!error}>
          <span>{selectedOption ? selectedOption.label : placeholder}</span>
          <Chevron>▾</Chevron>
        </Trigger>
        <AnimatePresence>
          {isOpen && (
            <Options initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              {options.map((opt) => (
                <Option key={opt.value} $active={opt.value === value} onClick={() => { onChange(opt.value); setIsOpen(false); }}>
                  {opt.label}
                </Option>
              ))}
            </Options>
          )}
        </AnimatePresence>
      </div>
      {error && <div style={{ marginTop: 8, fontSize: 12, color: '#ef4444' }}>{error}</div>}
    </Wrapper>
  );
};