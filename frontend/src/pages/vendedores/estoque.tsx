import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Package, Filter } from 'lucide-react';
import PainelLayout from '@/components/layout/PainelLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Table } from '@/components/ui/Table';
import { apiGet } from '@/lib/api';
import styled from 'styled-components';
import { colors } from '@/styles/tokens';
import GaleriaPro from '@/components/GaleriaPro';

interface Produto {
  sku: string;
  titulo: string;
  preco: number;
  estoque: number;
  origem: string;
  status: 'ativo' | 'inativo';
  imagens?: string[];
  data_importacao?: string;
}

type ProdutoApi = {
  id: number;
  sku: string;
  titulo: string;
  descricao?: string;
  preco: number;
  estoque_atual: number;
  origem: string;
  status: string;
  imagens?: string[];
};

function mapProdutoApiToUi(api: ProdutoApi): Produto {
  return {
    sku: api.sku,
    titulo: api.titulo,
    preco: api.preco,
    origem: api.origem,
    estoque: api.estoque_atual ?? 0,
    status: api.status?.toUpperCase() === 'ATIVO' ? 'ativo' : 'inativo',
    imagens: Array.isArray(api.imagens) ? api.imagens.filter(Boolean) : [],
  };
}

const origemOptions = [
  { value: '', label: 'Todas as Origens' },
  { value: 'MERCADO_LIVRE', label: 'Mercado Livre' },
  { value: 'SHOPIFY', label: 'Shopify' },
];

const Breadcrumb = styled.nav`
  display: flex;
  margin-bottom: 24px;
`;

const FiltersBar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
`;

const SearchWrap = styled.div`
  position: relative;
`;

const Thumb = styled.div`
  width: 48px; height: 48px; border-radius: 12px; overflow: hidden; background: #f1f5f9;
`;

const ThumbImg = styled.img`
  width: 100%; height: 100%; object-fit: cover;
`;

const ThumbEmpty = styled.div`
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: ${colors.textLight};
`;

const StatusBadge = styled.span<{ $ativo?: boolean }>`
  display: inline-block;
  padding: 6px 10px;
  border-radius: 9999px;
  font-size: 12px;
  ${({ $ativo }) => ($ativo ? `background: #dcfce7; color: #166534;` : `background: #f1f5f9; color: #1f2937;`)}
`;

const OriginBadge = styled.span`
  display: inline-block; padding: 6px 10px; border-radius: 9999px; font-size: 12px; background: #dbeafe; color: #1e40af;
`;

export default function EstoqueVendedores() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [origemFilter, setOrigemFilter] = useState('');

  const carregarProdutos = async () => {
    try {
      setLoading(true);
      const data = await apiGet<{ items: ProdutoApi[] }>('/estoque');
      const produtosApi = data.items ?? [];
      const produtosUi = produtosApi.map(mapProdutoApiToUi);
      setProdutos(produtosUi);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarProdutos();
  }, []);

  const produtosFiltrados = produtos.filter(produto => {
    const matchSearch = searchTerm === '' || 
      produto.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
      produto.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      produto.origem.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchOrigem = origemFilter === '' || produto.origem === origemFilter;
    
    return matchSearch && matchOrigem;
  });

  const columns = [
    {
      key: 'imagens' as keyof Produto,
      header: 'Imagem',
      render: (value: string[] | undefined) => <GaleriaPro imagens={Array.isArray(value) ? value : []} />,
    },
    {
      key: 'titulo' as keyof Produto,
      header: 'Produto',
      render: (value: string, item: Produto) => (
        <div>
          <div style={{ fontWeight: 600, color: colors.textDark }}>{value}</div>
          <div style={{ fontSize: 12, color: colors.textLight }}>{item.sku}</div>
        </div>
      ),
      sortable: true,
    },
    {
      key: 'preco' as keyof Produto,
      header: 'Preço',
      render: (value: number) => (
        <span style={{ fontWeight: 600, color: colors.textDark }}>R$ {value?.toFixed(2) || '0.00'}</span>
      ),
      sortable: true,
    },
    {
      key: 'estoque' as keyof Produto,
      header: 'Estoque',
      render: (value: number) => (
        <span style={{ fontWeight: 600, color: value > 10 ? '#16a34a' : value > 0 ? '#ca8a04' : '#dc2626' }}>{value || 0} un</span>
      ),
      sortable: true,
    },
    {
      key: 'origem' as keyof Produto,
      header: 'Origem',
      render: (value: string) => (
        <OriginBadge>{value === 'MERCADO_LIVRE' ? 'Mercado Livre' : value === 'SHOPIFY' ? 'Shopify' : value}</OriginBadge>
      ),
      sortable: true,
    },
    {
      key: 'status' as keyof Produto,
      header: 'Status',
      render: (value: string) => (
        <StatusBadge $ativo={value === 'ativo'}>{value === 'ativo' ? 'Ativo' : 'Inativo'}</StatusBadge>
      ),
    },
  ];

  return (
    <PainelLayout titulo="Estoque" tipoUsuario="vendedor">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <Breadcrumb aria-label="Breadcrumb">
          <ol style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <li style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: colors.textLight }}>
              <span>Dashboard</span>
            </li>
            <li>
              <span style={{ color: colors.primary, fontWeight: 500 }}>Estoque</span>
            </li>
          </ol>
        </Breadcrumb>
        <Card>
          <CardHeader>
            <FiltersBar>
              <div>
                <CardTitle>Gerenciamento de Estoque</CardTitle>
                <CardDescription>Visualize e gerencie todos os produtos do seu inventário</CardDescription>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Filter size={20} color={colors.textLight} />
                  <Select options={origemOptions} value={origemFilter} onChange={setOrigemFilter} placeholder="Filtrar por origem" />
                </div>
                <SearchWrap>
                  <Search size={20} color={colors.textLight} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
                  <Input type="text" placeholder="Buscar por SKU, nome ou origem" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
                </SearchWrap>
              </div>
            </FiltersBar>
          </CardHeader>
          <CardContent>
            <Table data={produtosFiltrados} columns={columns} itemsPerPage={20} />
          </CardContent>
        </Card>
      </motion.div>
    </PainelLayout>
  );
}