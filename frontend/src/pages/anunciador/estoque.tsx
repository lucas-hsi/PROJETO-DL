import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Package, Filter, RefreshCw, Clock, Plus, BarChart3, Edit3, X, Save, ExternalLink, Layers } from 'lucide-react';
import PainelLayout from '@/components/layout/PainelLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Table } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import ImportarProdutosButtonMelhorado from '@/components/ui/ImportarProdutosButtonMelhorado';
import { ToastContainer, useToast } from '@/components/ui/Toast';
import { apiGet, apiPost, apiPut } from '@/lib/api';
import styled from 'styled-components';
import { colors } from '@/styles/tokens';
import GaleriaPro from '@/components/GaleriaPro';
import SearchInput from '@/components/ui/SearchInput';

interface Produto {
  sku: string;
  titulo: string;
  preco: number;
  estoque: number;
  origem: string;
  status: 'ativo' | 'inativo';
  imagens?: string[];
  data_importacao?: string;
  descricao?: string;
  categoria?: string;
  part_number?: string;
  ml_id?: string;
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
  categoria?: string;
  part_number?: string;
  ml_id?: string;
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
    descricao: api.descricao,
    categoria: api.categoria,
    part_number: api.part_number,
    ml_id: api.ml_id,
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

 

const Thumb = styled.div`
  width: 48px; height: 48px; border-radius: 12px; overflow: hidden; background: #f1f5f9;
`;

const ThumbImg = styled.img`
  width: 100%; height: 100%; object-fit: cover;
`;

const ThumbEmpty = styled.div`
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: ${colors.textLight};
`;

const StatusBadge = styled.span<{ $ativo?: boolean; $estoque?: number }>`
  display: inline-block;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  ${({ $estoque }) => {
    if ($estoque === 0) return `background: #fef2f2; color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.15);`;
    if ($estoque && $estoque > 0) return `background: #f0fdf4; color: #16a34a; border: 1px solid rgba(22, 163, 74, 0.15);`;
    return `background: #f8fafc; color: #64748b; border: 1px solid rgba(100, 116, 139, 0.15);`;
  }}
`;

const OriginBadge = styled.span<{ $origem?: string }>`
  display: inline-block; 
  padding: 6px 12px; 
  border-radius: 8px; 
  font-size: 12px; 
  font-weight: 600;
  ${({ $origem }) => $origem === 'MERCADO_LIVRE' 
    ? `background: rgba(0, 102, 255, 0.08); color: #0066FF; border: 1px solid rgba(0, 102, 255, 0.15);`
    : `background: #dbeafe; color: #1e40af; border: 1px solid rgba(30, 64, 175, 0.15);`
  }
`;

 

const PremiumButton = styled(Button)`
  height: 42px !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  transition: all 0.2s ease !important;
  
  &:hover {
    transform: scale(1.02) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
  }
`;

const DrawerOverlay = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
`;

const DrawerContainer = styled(motion.div)`
  position: fixed;
  top: 0;
  right: 0;
  width: 500px;
  height: 100vh;
  background: white;
  box-shadow: -10px 0 25px rgba(0,0,0,0.1);
  z-index: 1001;
  display: flex;
  flex-direction: column;
`;

const DrawerHeader = styled.div`
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const DrawerTitle = styled.h2`
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
`;

const DrawerContent = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 24px;
`;

const DrawerFooter = styled.div`
  padding: 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const FormLabel = styled.label`
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #374151;
  font-size: 14px;
`;

const FormInput = styled(Input)`
  width: 100%;
`;

const FormTextArea = styled.textarea`
  width: 100%;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  min-height: 100px;
  
  &:focus {
    outline: none;
    border-color: #5B2EFF;
    box-shadow: 0 0 0 3px rgba(91, 46, 255, 0.1);
  }
`;

const ImageGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
  margin-top: 12px;
`;

const ImageItem = styled.div`
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #e5e7eb;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
`;

const ErrorMessage = styled.div`
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
`;

const TableRow = styled.tr`
  cursor: pointer;
  transition: background-color 0.2s ease;
  
  &:hover {
    background-color: #f8fafc;
  }
`;

export default function EstoqueAnunciador() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [origemFilter, setOrigemFilter] = useState('');
  const [sincronizando, setSincronizando] = useState(false);
  const [statusSincronizacao, setStatusSincronizacao] = useState<SincronizacaoStatus | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const { toasts, removeToast, success, error } = useToast();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Produto | null>(null);
  const [editedProduct, setEditedProduct] = useState<Produto | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string>('');

  const carregarProdutos = async (page = currentPage, size = pageSize) => {
    try {
      setLoading(true);
      const data = await apiGet<{
        items: ProdutoApi[];
        page: number;
        size: number;
        total: number;
        total_pages: number;
      }>(`/estoque?page=${page}&size=${size}&search=${searchTerm}&origem=${origemFilter}`);
      
      const produtosApi = data.items ?? [];
      const produtosUi = produtosApi.map(mapProdutoApiToUi);
      setProdutos(produtosUi);
      setCurrentPage(data.page);
      setTotalPages(data.total_pages);
      setTotalItems(data.total);
    } catch (err) {
      console.error('Erro ao carregar produtos:', err);
      error('Erro ao carregar produtos', 'Não foi possível carregar os produtos do estoque.');
    } finally {
      setLoading(false);
    }
  };

  const sincronizarProdutos = async (endpoint: string) => {
    try {
      setSincronizando(true);
      
      // Limpar status anterior
      setStatusSincronizacao(null);
      
      // Fazer a chamada inicial
      const response = await apiPost(endpoint);
      
      // Se for sincronização em background, mostrar mensagem apropriada
      if (endpoint.includes('/meli/sync/')) {
        success('Sincronização iniciada!', 'O processo está rodando em background.');
        
        // Para sincronizações em background, iniciar polling
        const interval = setInterval(async () => {
          try {
            const status = await apiGet<SincronizacaoStatus>('/estoque/meli/status');
            setStatusSincronizacao(status);
            
            if (status.status === 'concluido' || status.status === 'erro') {
              clearInterval(interval);
              setSincronizando(false);
              if (status.status === 'concluido') {
                carregarProdutos();
                success('Sincronização concluída!', `${status.progresso?.atual || 0} produtos processados.`);
              } else if (status.status === 'erro') {
                error('Erro na sincronização', 'Verifique os logs para mais detalhes.');
              }
            }
          } catch (statusError) {
            console.error('Erro ao verificar status:', statusError);
            clearInterval(interval);
            setSincronizando(false);
          }
        }, 3000);
      } else {
        // Para importações diretas, mostrar resultado imediatamente
        if (response && typeof response === 'object') {
          const importados = (response as any).importados || 0;
          const tempo = (response as any).tempo_execucao || 'N/A';
          success('Importação concluída!', `${importados} produtos importados em ${tempo}.`);
          carregarProdutos();
        }
        setSincronizando(false);
      }
    } catch (syncError: any) {
      console.error('Erro ao sincronizar:', syncError);
      error('Erro ao sincronizar produtos', syncError.message || 'Verifique sua conexão e tente novamente.');
      setSincronizando(false);
    }
  };

  useEffect(() => {
    carregarProdutos(1, pageSize);
  }, [searchTerm, origemFilter, pageSize]);

  useEffect(() => {
    if (currentPage > 1 || (searchTerm === '' && origemFilter === '')) {
      carregarProdutos(currentPage, pageSize);
    }
  }, [currentPage]);

  const openDrawer = (product: Produto) => {
    setSelectedProduct(product);
    setEditedProduct({ ...product });
    setDrawerOpen(true);
    setDrawerError('');
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedProduct(null);
    setEditedProduct(null);
    setDrawerError('');
  };

  const saveLocal = () => {
    if (!editedProduct) return;
    
    const updatedProdutos = produtos.map(p => 
      p.sku === editedProduct.sku ? editedProduct : p
    );
    setProdutos(updatedProdutos);
    success('✔ Produto atualizado localmente', 'As alterações foram salvas temporariamente.');
  };

  const validateProduct = (product: Produto): string[] => {
    const errors: string[] = [];
    
    if (!product.titulo || product.titulo.trim().length < 3) {
      errors.push('Título inválido (mínimo 3 caracteres)');
    }
    
    if (!product.preco || product.preco <= 0) {
      errors.push('Preço deve ser maior que zero');
    }
    
    if (product.estoque === undefined || product.estoque < 0) {
      errors.push('Estoque não pode ser negativo');
    }
    
    if (!product.imagens || product.imagens.length === 0) {
      errors.push('Pelos menos 1 imagem é obrigatória');
    }
    
    if (!product.categoria || product.categoria.trim().length < 2) {
      errors.push('Categoria inválida');
    }
    
    if (!product.descricao || product.descricao.trim().length < 10) {
      errors.push('Descrição muito curta (mínimo 10 caracteres)');
    }
    
    return errors;
  };

  const updateListingOnMercadoLivre = async (productId: string, payload: any) => {
    try {
      setDrawerLoading(true);
      setDrawerError('');
      
      const response = await apiPut(`/ml/products/${productId}`, payload);
      
      // Atualizar produto local com dados do ML
      const updatedProdutos = produtos.map(p => 
        p.ml_id === productId ? { ...p, ...payload } : p
      );
      setProdutos(updatedProdutos);
      
      success('✔ Anúncio atualizado no Mercado Livre', 'As alterações foram publicadas com sucesso.');
      closeDrawer();
      
    } catch (err: any) {
      console.error('Erro ao atualizar no ML:', err);
      setDrawerError('⚠️ Não foi possível atualizar o anúncio. Verifique os dados e tente novamente.');
      error('⚠️ Erro ao atualizar no Mercado Livre', err.message || 'Tente novamente mais tarde.');
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleEditOnMercadoLivre = async () => {
    if (!editedProduct || !editedProduct.ml_id) {
      setDrawerError('⚠️ Produto não possui ID do Mercado Livre');
      return;
    }
    
    const validationErrors = validateProduct(editedProduct);
    if (validationErrors.length > 0) {
      setDrawerError(`⚠️ Corrija antes de atualizar:\n• ${validationErrors.join('\n• ')}`);
      return;
    }
    
    const payload = {
      title: editedProduct.titulo,
      price: editedProduct.preco,
      available_quantity: editedProduct.estoque,
      pictures: editedProduct.imagens?.map(url => ({ source: url })) || [],
      description: editedProduct.descricao,
      category_id: editedProduct.categoria
    };
    
    await updateListingOnMercadoLivre(editedProduct.ml_id, payload);
  };



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
          {item.part_number && (
            <div style={{ fontSize: 11, color: colors.textLight }}>PN: {item.part_number}</div>
          )}
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
        <OriginBadge $origem={value}>{value === 'MERCADO_LIVRE' ? 'Mercado Livre' : value === 'SHOPIFY' ? 'Shopify' : value}</OriginBadge>
      ),
      sortable: true,
    },
    {
      key: 'status' as keyof Produto,
      header: 'Status',
      render: (value: string, item: Produto) => {
        const statusReal = item.estoque > 0 ? 'Ativo' : 'Pausado';
        return <StatusBadge $estoque={item.estoque}>{statusReal}</StatusBadge>;
      },
    },
  ];

  return (
    <>
      <ToastContainer toasts={toasts} onClose={removeToast} />
      <PainelLayout titulo="Estoque" tipoUsuario="anunciador">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          

          <Card>
            <CardContent>
              <ActionsBar>
                <PremiumButton variant="primary" onClick={() => sincronizarProdutos('/estoque/importar-meli-todos-status')} disabled={sincronizando}>
                  <Plus size={16} />
                  <span>Apenas importação completa</span>
                </PremiumButton>
                <PremiumButton variant="secondary" onClick={() => sincronizarProdutos('/estoque/importar-meli-incremental?hours=24')} disabled={sincronizando}>
                  <Clock size={16} />
                  <span>Recentes (24h)</span>
                </PremiumButton>
                <PremiumButton variant="secondary" onClick={() => sincronizarProdutos('/estoque/importar-meli-incremental?hours=168')} disabled={sincronizando}>
                  <Clock size={16} />
                  <span>Últimos 7 dias</span>
                </PremiumButton>
                <PremiumButton variant="secondary" onClick={() => sincronizarProdutos('/meli/sync/todos-status-start')} disabled={sincronizando}>
                  <RefreshCw size={16} />
                  <span>Sync Completa (BG)</span>
                </PremiumButton>
                <PremiumButton variant="secondary" onClick={() => sincronizarProdutos('/meli/sync/incremental-start')} disabled={sincronizando}>
                  <RefreshCw size={16} />
                  <span>Sync Incremental</span>
                </PremiumButton>
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
                <SearchInput
                  value={searchTerm}
                  onChange={setSearchTerm}
                  placeholder="Buscar por SKU, nome ou origem"
                  debounceMs={300}
                />
              </FiltersBar>

              <ImportarProdutosButtonMelhorado onFinish={carregarProdutos} />

              <Table 
                data={produtos} 
                columns={columns} 
                itemsPerPage={pageSize}
                currentPage={currentPage}
                totalPages={totalPages}
                totalItems={totalItems}
                onPageChange={setCurrentPage}
                onPageSizeChange={setPageSize}
                pageSizeOptions={[50, 100, 200, 500]}
                loading={loading}
                onRowClick={openDrawer}
                rowComponent={TableRow}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Drawer */}
        <AnimatePresence>
          {drawerOpen && (
            <>
              <DrawerOverlay
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={closeDrawer}
              />
              <DrawerContainer
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              >
                <DrawerHeader>
                  <DrawerTitle>Editar Produto</DrawerTitle>
                  <Button variant="ghost" onClick={closeDrawer}>
                    <X size={20} />
                  </Button>
                </DrawerHeader>
                
                <DrawerContent>
                  {drawerLoading && (
                    <LoadingOverlay>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Atualizando no Mercado Livre...</div>
                        <div style={{ color: '#6b7280' }}>Aguarde um momento</div>
                      </div>
                    </LoadingOverlay>
                  )}
                  
                  {drawerError && (
                    <ErrorMessage>
                      {drawerError.split('\n').map((line, index) => (
                        <div key={index}>{line}</div>
                      ))}
                    </ErrorMessage>
                  )}

                  {editedProduct && (
                    <>
                      <FormGroup>
                        <FormLabel>Fotos do Produto</FormLabel>
                        <ImageGrid>
                          {editedProduct.imagens?.map((img, index) => (
                            <ImageItem key={index}>
                              <img src={img} alt={`Imagem ${index + 1}`} />
                            </ImageItem>
                          ))}
                        </ImageGrid>
                      </FormGroup>

                      <FormGroup>
                        <FormLabel>Título</FormLabel>
                        <FormInput
                          value={editedProduct.titulo}
                          onChange={(e) => setEditedProduct({ ...editedProduct, titulo: e.target.value })}
                        />
                      </FormGroup>

                      <FormGroup>
                        <FormLabel>SKU</FormLabel>
                        <FormInput value={editedProduct.sku} disabled />
                      </FormGroup>

                      {editedProduct.part_number && (
                        <FormGroup>
                          <FormLabel>Part Number</FormLabel>
                          <FormInput value={editedProduct.part_number} disabled />
                        </FormGroup>
                      )}

                      <FormGroup>
                        <FormLabel>Preço (R$)</FormLabel>
                        <FormInput
                          type="number"
                          step="0.01"
                          value={editedProduct.preco}
                          onChange={(e) => setEditedProduct({ ...editedProduct, preco: parseFloat(e.target.value) || 0 })}
                        />
                      </FormGroup>

                      <FormGroup>
                        <FormLabel>Estoque</FormLabel>
                        <FormInput
                          type="number"
                          value={editedProduct.estoque}
                          onChange={(e) => setEditedProduct({ ...editedProduct, estoque: parseInt(e.target.value) || 0 })}
                        />
                      </FormGroup>

                      <FormGroup>
                        <FormLabel>Descrição</FormLabel>
                        <FormTextArea
                          value={editedProduct.descricao || ''}
                          onChange={(e) => setEditedProduct({ ...editedProduct, descricao: e.target.value })}
                        />
                      </FormGroup>

                      <FormGroup>
                        <FormLabel>Categoria</FormLabel>
                        <FormInput
                          value={editedProduct.categoria || ''}
                          onChange={(e) => setEditedProduct({ ...editedProduct, categoria: e.target.value })}
                        />
                      </FormGroup>
                    </>
                  )}
                </DrawerContent>
                
                <DrawerFooter>
                  <Button variant="secondary" onClick={closeDrawer}>
                    Cancelar
                  </Button>
                  <Button variant="secondary" onClick={saveLocal}>
                    <Save size={16} />
                    Salvar Localmente
                  </Button>
                  {editedProduct?.origem === 'MERCADO_LIVRE' && editedProduct.ml_id && (
                    <PremiumButton variant="primary" onClick={handleEditOnMercadoLivre} disabled={drawerLoading}>
                      <ExternalLink size={16} />
                      Editar no Mercado Livre
                    </PremiumButton>
                  )}
                </DrawerFooter>
              </DrawerContainer>
            </>
          )}
        </AnimatePresence>
      </PainelLayout>
    </>
  );
}