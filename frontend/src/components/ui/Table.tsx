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

export function Table<T>({ data, columns, itemsPerPage = 10, className }: TableProps<T>) {
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(data.length / itemsPerPage));
  const paginated = useMemo(() => {
    const start = (page - 1) * itemsPerPage;
    return data.slice(start, start + itemsPerPage);
  }, [data, page, itemsPerPage]);

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
            {paginated.map((item, idx) => (
              <Tr key={idx} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                {columns.map((c) => (
                  <Td key={String(c.key)}>
                    {c.render ? c.render((item as any)[c.key], item) : String((item as any)[c.key] ?? '')}
                  </Td>
                ))}
              </Tr>
            ))}
          </Body>
        </table>
        <Footer>
          <div style={{ fontSize: 13, color: colors.textLight }}>Página {page} de {totalPages}</div>
          <Pager>
            <PagerBtn onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
              <ChevronLeft size={16} />
            </PagerBtn>
            <PagerBtn onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
              <ChevronRight size={16} />
            </PagerBtn>
          </Pager>
        </Footer>
      </TableWrapper>
    </div>
  );
}