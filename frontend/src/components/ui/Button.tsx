import React from 'react';
import styled, { keyframes, css } from 'styled-components';
import { colors } from '@/styles/tokens';

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: React.ReactNode;
}

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const BaseButton = styled.button<{ $variant: Variant; $size: Size; $loading?: boolean }>`
  border: none;
  border-radius: 12px;
  padding: ${({ $size }) => ($size === 'sm' ? '8px 12px' : $size === 'lg' ? '16px 24px' : '12px 18px')};
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  ${({ $variant }) =>
    $variant === 'primary'
      ? `background: linear-gradient(135deg, ${colors.primary}, ${colors.secondary}); color: ${colors.white}; box-shadow: 0 8px 30px rgba(79,70,229,0.25);`
      : $variant === 'secondary'
      ? `background: ${colors.card}; color: ${colors.textDark}; border: 1px solid ${colors.border}; backdrop-filter: blur(14px);`
      : $variant === 'outline'
      ? `background: transparent; color: ${colors.primary}; border: 2px solid ${colors.primary};`
      : $variant === 'danger'
      ? `background: linear-gradient(135deg, #ef4444, #dc2626); color: ${colors.white}; box-shadow: 0 8px 30px rgba(239,68,68,0.25);`
      : `background: transparent; color: ${colors.textLight};`}
  ${({ $loading }) => ($loading ? 'opacity: 0.6; cursor: not-allowed;' : '')}
  &:hover { opacity: 0.92; transform: translateY(-2px); }
`;

const Spinner = styled.div`
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-bottom-color: transparent;
  animation: ${css`${spin} 0.8s linear infinite`};
`;

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, children, disabled, ...props }, ref) => {
    return (
      <BaseButton ref={ref} $variant={variant} $size={size} $loading={loading} disabled={disabled || loading} {...props}>
        {loading && <Spinner />}
        {children}
      </BaseButton>
    );
  }
);

Button.displayName = 'Button';