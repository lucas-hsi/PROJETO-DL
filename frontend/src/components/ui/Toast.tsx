import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Info, AlertCircle, X } from 'lucide-react';
import styled from 'styled-components';
import { colors, radius, shadows } from '@/styles/tokens';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  onClose: (id: string) => void;
}

const toastConfig = {
  success: {
    icon: CheckCircle,
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-800',
    iconColor: 'text-green-500',
  },
  error: {
    icon: XCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    iconColor: 'text-red-500',
  },
  info: {
    icon: Info,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-500',
  },
  warning: {
    icon: AlertCircle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-800',
    iconColor: 'text-yellow-500',
  },
};

export const Toast: React.FC<ToastProps> = ({ id, type, title, message, onClose }) => {
  const config = toastConfig[type];
  const Icon = config.icon;

  React.useEffect(() => {
    const timer = setTimeout(() => {
      onClose(id);
    }, 5000);
    return () => clearTimeout(timer);
  }, [id, onClose]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.9 }}
      className={`w-full max-w-sm ${config.bgColor} border ${config.borderColor} rounded-lg shadow-lg p-4`}
    >
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <Icon className={`h-5 w-5 ${config.iconColor}`} />
        </div>
        <div className="ml-3 flex-1">
          <h3 className={`text-sm font-medium ${config.textColor}`}>
            {title}
          </h3>
          {message && (
            <p className={`mt-1 text-sm ${config.textColor} opacity-80`}>
              {message}
            </p>
          )}
        </div>
        <div className="ml-4 flex-shrink-0">
          <button
            onClick={() => onClose(id)}
            className={`${config.textColor} hover:opacity-70 focus:outline-none`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

interface ToastContainerProps {
  toasts: Array<{
    id: string;
    type: ToastType;
    title: string;
    message?: string;
  }>;
  onClose: (id: string) => void;
}

const ToastStack = styled.div`
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const ToastBox = styled(motion.div)<{ $type: ToastType }>`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: ${radius.md};
  box-shadow: ${shadows.base};
  background: ${colors.card};
  border: 1px solid ${colors.border};
`;

const Title = styled.div`
  font-weight: 600;
  color: ${colors.textDark};
`;

const Msg = styled.div`
  font-size: 13px;
  color: ${colors.textLight};
`;

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onClose }) => {
  return (
    <ToastStack>
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastBox key={toast.id} $type={toast.type} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
            {toast.type === 'success' && <CheckCircle size={18} color="#16a34a" />}
            {toast.type === 'error' && <XCircle size={18} color="#dc2626" />}
            {toast.type === 'info' && <Info size={18} color="#0284c7" />}
            {toast.type === 'warning' && <AlertCircle size={18} color="#f59e0b" />}
            <div style={{ flex: 1 }}>
              <Title>{toast.title}</Title>
              {toast.message && <Msg>{toast.message}</Msg>}
            </div>
            <button onClick={() => onClose(toast.id)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: colors.textLight }}>
              <X size={16} />
            </button>
          </ToastBox>
        ))}
      </AnimatePresence>
    </ToastStack>
  );
};

// Hook para gerenciar toasts
export const useToast = () => {
  const [toasts, setToasts] = React.useState<Array<{
    id: string;
    type: ToastType;
    title: string;
    message?: string;
  }>>([]);

  const addToast = (type: ToastType, title: string, message?: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, type, title, message }]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return {
    toasts,
    addToast,
    removeToast,
    success: (title: string, message?: string) => addToast('success', title, message),
    error: (title: string, message?: string) => addToast('error', title, message),
    info: (title: string, message?: string) => addToast('info', title, message),
    warning: (title: string, message?: string) => addToast('warning', title, message),
  };
};