import React from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { colors, radius, shadows, typography } from '@/styles/tokens';

const CardBase = styled(motion.div)`
  background: ${colors.card};
  backdrop-filter: blur(14px);
  border-radius: ${radius.lg};
  box-shadow: ${shadows.base};
  border: 1px solid ${colors.border};
  transition: all 0.3s ease;
  &:hover { transform: translateY(-2px); box-shadow: ${shadows.hover}; }
`;

export const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <CardBase initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      {children}
    </CardBase>
  );
};

const Header = styled.div`
  padding: 24px;
  padding-bottom: 16px;
`;

export const CardHeader: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Header>{children}</Header>;
};

const Title = styled.h3`
  font-size: 18px;
  font-weight: ${typography.weightSemibold};
  color: ${colors.textDark};
`;

export const CardTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Title>{children}</Title>;
};

const Description = styled.p`
  font-size: 14px;
  color: ${colors.textLight};
  margin-top: 4px;
`;

export const CardDescription: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Description>{children}</Description>;
};

const Content = styled.div`
  padding: 24px;
  padding-top: 0;
`;

export const CardContent: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Content>{children}</Content>;
};

export const CardFooter: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <Content>{children}</Content>;
};