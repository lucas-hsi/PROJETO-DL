import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { colors, radius, shadows, typography } from '@/styles/tokens';

type Column<T> = {
  key: keyof T;
  header: string;
  render?: (value: any, item: T) => React.ReactNode;
  sortable?: boolean;
};

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  itemsPerPage?: number;
  className?: string;
  currentPage?: number;
  totalPages?: number;
  totalItems?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  loading?: boolean;
  onRowClick?: (item: T) => void;
  rowComponent?: React.ComponentType<any>;
}

const TableWrapper = styled.div`
  width: 100%;
  overflow: hidden;
  border-radius: ${radius.md};
  box-shadow: ${shadows.base};
  background: ${colors.card};
  backdrop-filter: blur(14px);
  border: 1px solid ${colors.border};
`;

const Header = styled.thead`
  background: rgba(255,255,255,0.9);
`;

const Th = styled.th`
  text-align: left;
  padding: 14px 16px;
  font-weight: ${typography.weightMedium};
  color: ${colors.textDark};
`;

const Body = styled.tbody`
  background: ${colors.card};
`;

const Tr = styled(motion.tr)`
  border-top: 1px solid rgba(0,0,0,0.06);
`;

const Td = styled.td`
  padding: 12px 16px;
  color: ${colors.textDark};
`;

const Footer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid ${colors.border};
  background: rgba(255,255,255,0.8);
`;

const PageSizeSelector = styled.select`
  padding: 6px 10px;
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  background: ${colors.card};
  color: ${colors.textDark};
  font-size: 13px;
  cursor: pointer;
  &:focus {
    outline: none;
    border-color: ${colors.primary};
  }
`;

const PageInfo = styled.div`
  font-size: 13px;
  color: ${colors.textLight};
`;

const PaginationControls = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const Pager = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const PagerBtn = styled.button`
  border: 1px solid ${colors.border};
  background: ${colors.card};
  color: ${colors.textDark};
  border-radius: ${radius.sm};
  padding: 6px 10px;
  cursor: pointer;
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

export function Table<T>({ 
  data, 
  columns, 
  itemsPerPage = 50, 
  className, 
  currentPage = 1, 
  totalPages = 1, 
  totalItems = 0, 
  onPageChange, 
  onPageSizeChange, 
  pageSizeOptions = [50, 100, 200, 500],
  loading = false,
  onRowClick,
  rowComponent: RowComponent = Tr
}: TableProps<T>) {
  const [localPage, setLocalPage] = useState(1);
  const [localPageSize, setLocalPageSize] = useState(itemsPerPage);
  
  // Usar paginação externa (server-side) ou interna (client-side)
  const isServerSide = !!(onPageChange && totalPages > 1);
  const currentPageValue = isServerSide ? currentPage : localPage;
  const currentPageSize = isServerSide ? itemsPerPage : localPageSize;
  const totalPagesValue = isServerSide ? totalPages : Math.max(1, Math.ceil(data.length / currentPageSize));
  const totalItemsValue = isServerSide ? totalItems : data.length;
  
  // Dados paginados - sempre usar useMemo para manter ordem dos hooks
  const displayData = useMemo(() => {
    if (isServerSide) {
      return data; // Server-side: retornar todos os dados
    } else {
      // Client-side: aplicar paginação
      const start = (currentPageValue - 1) * currentPageSize;
      return data.slice(start, start + currentPageSize);
    }
  }, [data, currentPageValue, currentPageSize, isServerSide]);

  const handlePageChange = (newPage: number) => {
    if (isServerSide && onPageChange) {
      onPageChange(newPage);
    } else {
      setLocalPage(newPage);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    setLocalPage(1); // Resetar para página 1 quando mudar tamanho
    if (isServerSide && onPageSizeChange) {
      onPageSizeChange(newSize);
    } else {
      setLocalPageSize(newSize);
    }
  };

  const startItem = (currentPageValue - 1) * currentPageSize + 1;
  const endItem = Math.min(currentPageValue * currentPageSize, totalItemsValue);

  return (
    <div className={className}>
      <TableWrapper>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <Header>
            <tr>
              {columns.map((c) => (
                <Th key={String(c.key)}>{c.header}</Th>
              ))}
            </tr>
          </Header>
          <Body>
            {loading ? (
              <tr>
                <Td colSpan={columns.length} style={{ textAlign: 'center', padding: '40px', color: colors.textLight }}>
                  ⏳ Carregando produtos...
                </Td>
              </tr>
            ) : displayData.length === 0 ? (
              <tr>
                <Td colSpan={columns.length} style={{ textAlign: 'center', padding: '40px', color: colors.textLight }}>
                  📦 Nenhum produto encontrado
                </Td>
              </tr>
            ) : (
              displayData.map((item, idx) => (
                <RowComponent 
                  key={idx} 
                  initial={{ opacity: 0 }} 
                  animate={{ opacity: 1 }}
                  onClick={() => onRowClick?.(item)}
                  style={{ cursor: onRowClick ? 'pointer' : 'default' }}
                >
                  {columns.map((c) => (
                    <Td key={String(c.key)}>
                      {c.render ? c.render((item as any)[c.key], item) : String((item as any)[c.key] ?? '')}
                    </Td>
                  ))}
                </RowComponent>
              ))
            )}
          </Body>
        </table>
        <Footer>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {onPageSizeChange && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: 13, color: colors.textLight }}>Itens por página:</span>
                <PageSizeSelector 
                  value={currentPageSize} 
                  onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                >
                  {pageSizeOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </PageSizeSelector>
              </div>
            )}
            <PageInfo>
              {startItem}-{endItem} de {totalItemsValue} itens
              {isServerSide && totalPagesValue > 1 && ` • Página ${currentPageValue} de ${totalPagesValue}`}
            </PageInfo>
          </div>
          <PaginationControls>
            <PagerBtn onClick={() => handlePageChange(currentPageValue - 1)} disabled={currentPageValue === 1}>
              <ChevronLeft size={16} />
            </PagerBtn>
            <PagerBtn onClick={() => handlePageChange(currentPageValue + 1)} disabled={currentPageValue >= totalPagesValue}>
              <ChevronRight size={16} />
            </PagerBtn>
          </PaginationControls>
        </Footer>
      </TableWrapper>
    </div>
  );
}