import { css } from "styled-components";
import { colors, shadows, radius } from "@/styles/tokens";

export const glassCard = css`
  background: ${colors.card};
  backdrop-filter: blur(14px);
  border-radius: ${radius.lg};
  box-shadow: ${shadows.base};
  border: 1px solid ${colors.border};
  transition: all 0.3s ease;
  &:hover {
    transform: translateY(-2px);
    box-shadow: ${shadows.hover};
  }
`;

export const gradientPrimary = css`
  background: linear-gradient(135deg, ${colors.primary}, ${colors.secondary});
`;

export const clickable = css`
  cursor: pointer;
  transition: all 0.25s ease;
  &:hover {
    opacity: 0.9;
    transform: translateY(-2px);
  }
`;