import React from 'react';
import styled from 'styled-components';
import { colors, typography, radius } from '@/styles/tokens';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

const Wrapper = styled.div`
  width: 100%;
`;

const Label = styled.label`
  display: block;
  font-size: 12px;
  font-weight: ${typography.weightMedium};
  color: ${colors.textDark};
  margin-bottom: 8px;
`;

const FieldWrapper = styled.div`
  position: relative;
`;

const Icon = styled.div`
  position: absolute;
  inset: 0 auto 0 12px;
  display: flex;
  align-items: center;
  color: ${colors.textLight};
`;

const Field = styled.input<{ $hasIcon?: boolean; $hasError?: boolean }>`
  width: 100%;
  border-radius: ${radius.md};
  border: 1px solid ${colors.border};
  background: ${colors.card};
  backdrop-filter: blur(14px);
  color: ${colors.textDark};
  padding: ${({ $hasIcon }) => ($hasIcon ? '12px 12px 12px 40px' : '12px')};
  outline: none;
  transition: all 0.2s ease;
  &::placeholder { color: ${colors.textLight}; }
  &:focus { border-color: ${colors.primary}; box-shadow: 0 0 0 3px rgba(79,70,229,0.2); }
  ${({ $hasError }) => ($hasError ? `border-color: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.2);` : '')}
`;

const ErrorText = styled.p`
  margin-top: 8px;
  font-size: 12px;
  color: #ef4444;
`;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    return (
      <Wrapper>
        {label && <Label htmlFor={inputId}>{label}</Label>}
        <FieldWrapper>
          {icon && <Icon>{icon}</Icon>}
          <Field ref={ref} id={inputId} $hasIcon={!!icon} $hasError={!!error} {...props} />
        </FieldWrapper>
        {error && <ErrorText>{error}</ErrorText>}
      </Wrapper>
    );
  }
);

Input.displayName = 'Input';