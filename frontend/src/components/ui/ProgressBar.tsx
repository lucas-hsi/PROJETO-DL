import React from 'react';
import styled, { keyframes, css } from 'styled-components';
import { colors } from '@/styles/tokens';

interface ProgressBarProps {
  progress: number; // 0-100
  status: 'idle' | 'running' | 'paused' | 'error' | 'completed';
  message?: string;
  showPercentage?: boolean;
  size?: 'small' | 'medium' | 'large';
  animated?: boolean;
}

const pulse = keyframes`
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
`;

const slideIn = keyframes`
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
`;

const Container = styled.div<{ size: 'small' | 'medium' | 'large' }>`
  width: 100%;
  font-family: inherit;
  ${props => {
    switch (props.size) {
      case 'small':
        return 'font-size: 12px;';
      case 'large':
        return 'font-size: 16px;';
      default:
        return 'font-size: 14px;';
    }
  }}
`;

const ProgressTrack = styled.div<{ size: ProgressBarProps['size']; status: ProgressBarProps['status'] }>`
  width: 100%;
  height: ${props => {
    switch (props.size) {
      case 'small': return '4px';
      case 'large': return '12px';
      default: return '8px';
    }
  }};
  background-color: ${props => {
    switch (props.status) {
      case 'error': return '#fee2e2';
      case 'completed': return '#dcfce7';
      default: return '#e5e7eb';
    }
  }};
  border-radius: 9999px;
  overflow: hidden;
  position: relative;
  transition: background-color 0.3s ease;
`;

const ProgressFill = styled.div<{ 
  progress: number; 
  status: ProgressBarProps['status'];
  animated: boolean;
}>`
  height: 100%;
  width: ${props => Math.min(Math.max(props.progress, 0), 100)}%;
  background: ${props => {
    switch (props.status) {
      case 'error':
        return 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
      case 'completed':
        return 'linear-gradient(90deg, #22c55e 0%, #16a34a 100%)';
      case 'running':
        return 'linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)';
      case 'paused':
        return 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
      default:
        return 'linear-gradient(90deg, #6b7280 0%, #4b5563 100%)';
    }
  }};
  border-radius: 9999px;
  transition: width 0.4s ease, background 0.3s ease;
  position: relative;
  overflow: hidden;
  
  ${props => props.animated && props.status === 'running' && css`
    &::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.3) 50%,
        transparent 100%
      );
      animation: ${slideIn} 1.5s ease-in-out infinite;
    }
  `}
`;

const StatusMessage = styled.div<{ status: ProgressBarProps['status'] }>`
  margin-top: 8px;
  color: ${props => {
    switch (props.status) {
      case 'error': return '#dc2626';
      case 'completed': return '#16a34a';
      case 'running': return '#2563eb';
      case 'paused': return '#d97706';
      default: return colors.textDark;
    }
  }};
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  
  ${props => props.status === 'running' && css`
    animation: ${pulse} 2s ease-in-out infinite;
  `}
`;

const Percentage = styled.span`
  font-weight: 600;
  margin-left: 4px;
`;

const StatusIcon = styled.span<{ status: ProgressBarProps['status'] }>`
  font-size: 1.2em;
`;

const getStatusIcon = (status: ProgressBarProps['status']): string => {
  switch (status) {
    case 'running': return '⏳';
    case 'completed': return '✅';
    case 'error': return '❌';
    case 'paused': return '⏸️';
    default: return '📊';
  }
};

const getStatusText = (status: ProgressBarProps['status']): string => {
  switch (status) {
    case 'running': return 'Processando...';
    case 'completed': return 'Concluído!';
    case 'error': return 'Erro ao processar';
    case 'paused': return 'Pausado';
    default: return 'Aguardando...';
  }
};

export default function ProgressBar({
  progress,
  status,
  message,
  showPercentage = true,
  size = 'medium',
  animated = true,
}: ProgressBarProps) {
  const displayMessage = message || getStatusText(status);
  
  return (
    <Container size={size}>
      <ProgressTrack status={status} size={size}>
        <ProgressFill 
          progress={progress} 
          status={status} 
          animated={animated}
        />
      </ProgressTrack>
      <StatusMessage status={status}>
        <StatusIcon status={status}>{getStatusIcon(status)}</StatusIcon>
        <span>{displayMessage}</span>
        {showPercentage && status === 'running' && (
          <Percentage>{Math.round(progress)}%</Percentage>
        )}
      </StatusMessage>
    </Container>
  );
}