import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Package, Filter, RefreshCw, Clock, Plus, BarChart3 } from 'lucide-react';
import PainelLayout from '@/components/layout/PainelLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Table } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import ImportarProdutosButton from '@/components/ui/ImportarProdutosButton';
import { ToastContainer, useToast } from '@/components/ui/Toast';
import { apiGet, apiPost } from '@/lib/api';
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

interface SincronizacaoStatus {
  status: string;
  progresso?: {
    atual: number;
    total: number;
    mensagem: string;
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

const ActionsBar = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
`;

const SyncStatus = styled(motion.div)`
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 12px;
  padding: 16px;
`;

const FiltersBar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
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

export default function EstoqueAnunciador() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [origemFilter, setOrigemFilter] = useState('');
  const [sincronizando, setSincronizando] = useState(false);
  const [statusSincronizacao, setStatusSincronizacao] = useState<SincronizacaoStatus | null>(null);
  const { toasts, removeToast, success, error } = useToast();

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

  const sincronizarProdutos = async (endpoint: string) => {
    try {
      setSincronizando(true);
      await apiPost(endpoint);
      // Iniciar polling do status
      const interval = setInterval(async () => {
        try {
          const status = await apiGet<SincronizacaoStatus>('/estoque/meli/status');
          setStatusSincronizacao(status);
          
          if (status.status === 'concluido' || status.status === 'erro') {
            clearInterval(interval);
            setSincronizando(false);
            if (status.status === 'concluido') {
              carregarProdutos();
              success('Sincronização concluída com sucesso!', 'Os produtos foram atualizados.');
            } else if (status.status === 'erro') {
              error('Erro na sincronização', 'Ocorreu um erro ao sincronizar os produtos.');
            }
          }
        } catch (statusError) {
          console.error('Erro ao verificar status:', statusError);
          clearInterval(interval);
          setSincronizando(false);
        }
      }, 3000);
    } catch (syncError) {
      console.error('Erro ao sincronizar:', syncError);
      error('Erro ao sincronizar produtos', 'Verifique sua conexão e tente novamente.');
      setSincronizando(false);
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
    <>
      <ToastContainer toasts={toasts} onClose={removeToast} />
      <PainelLayout titulo="Estoque" tipoUsuario="anunciador">
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
              <div>
                <CardTitle>Gerenciamento de Estoque</CardTitle>
                <CardDescription>Visualize, gerencie e sincronize todos os produtos do seu inventário</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <ActionsBar>
                <Button variant="primary" onClick={() => sincronizarProdutos('/estoque/importar-meli?novos=true')} disabled={sincronizando}>
                  <Plus size={16} />
                  <span>Sincronizar Novos Anúncios</span>
                </Button>
                <Button variant="secondary" onClick={() => sincronizarProdutos('/estoque/importar-meli?dias=15')} disabled={sincronizando}>
                  <Clock size={16} />
                  <span>Últimos 15 dias</span>
                </Button>
                <Button variant="secondary" onClick={() => sincronizarProdutos('/estoque/importar-meli?limit=500')} disabled={sincronizando}>
                  <RefreshCw size={16} />
                  <span>Atualizar Tudo</span>
                </Button>
              </ActionsBar>

              <AnimatePresence>
                {statusSincronizacao && statusSincronizacao.progresso && (
                  <SyncStatus initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <BarChart3 size={20} color={colors.secondary} />
                      <div style={{ flex: 1 }}>
                        <p style={{ fontSize: 13, fontWeight: 600, color: colors.textDark }}>{statusSincronizacao.progresso.mensagem}</p>
                        <div style={{ marginTop: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, color: colors.textLight, marginBottom: 4 }}>
                            <span>Progresso</span>
                            <span>{statusSincronizacao.progresso.atual} de {statusSincronizacao.progresso.total}</span>
                          </div>
                          <div style={{ width: '100%', background: 'rgba(99,102,241,0.25)', borderRadius: 9999, height: 8 }}>
                            <div style={{ background: colors.secondary, height: 8, borderRadius: 9999, width: `${(statusSincronizacao.progresso.atual / statusSincronizacao.progresso.total) * 100}%`, transition: 'width 300ms ease' }} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </SyncStatus>
                )}
              </AnimatePresence>

              <FiltersBar>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Filter size={20} color={colors.textLight} />
                  <Select options={origemOptions} value={origemFilter} onChange={setOrigemFilter} placeholder="Filtrar por origem" />
                </div>
                <SearchWrap>
                  <Search size={20} color={colors.textLight} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
                  <Input type="text" placeholder="Buscar por SKU, nome ou origem" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
                </SearchWrap>
              </FiltersBar>

              <ImportarProdutosButton onFinish={carregarProdutos} />

              <Table data={produtosFiltrados} columns={columns} itemsPerPage={20} />
            </CardContent>
          </Card>
        </motion.div>
      </PainelLayout>
    </>
  );
}