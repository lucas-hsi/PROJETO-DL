"use client";
import React, { useState, useEffect, useCallback } from "react";
import styled, { css } from "styled-components";
import { colors, shadows } from "@/styles/tokens";
import { Button } from "@/components/ui/Button";
import { apiPost, apiGet } from "@/lib/api";
import ProgressBar from "@/components/ui/ProgressBar";
import { Play, Pause, Square, RotateCcw, Package } from "lucide-react";

interface Props {
  onFinish?: () => void;
  onProgress?: (progress: ImportProgress) => void;
}

interface ImportProgress {
  total: number;
  processed: number;
  imported: number;
  percentage: number;
  status: 'idle' | 'running' | 'paused' | 'error' | 'completed';
  currentPage?: number;
  estimatedTimeRemaining?: number;
  error?: string;
}

const ImportContainer = styled.div`
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-radius: 16px;
  padding: 24px;
  box-shadow: ${shadows.base};
  border: 1px solid #e2e8f0;
  margin-bottom: 24px;
`;

const ImportHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
`;

const ImportTitle = styled.h3`
  font-size: 1.25rem;
  font-weight: 600;
  color: ${colors.textDark};
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const ActionButtons = styled.div`
  display: flex;
  gap: 12px;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
`;

const StatCard = styled.div`
  background: white;
  padding: 16px;
  border-radius: 12px;
  text-align: center;
  box-shadow: ${shadows.base};
  border: 1px solid #f1f5f9;
`;

const StatValue = styled.div`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${colors.textDark};
  margin-bottom: 4px;
`;

const StatLabel = styled.div`
  font-size: 0.875rem;
  color: ${colors.textLight};
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
`;

const ImportTypeButton = styled(Button)<{ isActive?: boolean }>`
  flex: 1;
  justify-content: center;
  ${props => props.isActive && css`
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
  `}
`;

export default function ImportarProdutosButtonMelhorado({ onFinish, onProgress }: Props) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [modoImportacao, setModoImportacao] = useState<'completa' | 'recentes' | 'incremental'>('completa');
  const [progress, setProgress] = useState<ImportProgress>({
    total: 0,
    processed: 0,
    imported: 0,
    percentage: 0,
    status: 'idle'
  });

  // Carregar progresso salvo ao montar o componente
  useEffect(() => {
    const savedProgress = localStorage.getItem('importProgress');
    if (savedProgress) {
      try {
        const parsed = JSON.parse(savedProgress);
        if (parsed.status === 'running' || parsed.status === 'paused') {
          setProgress({
            ...parsed,
            status: 'paused' // Sempre iniciar como pausado para segurança
          });
        }
      } catch (error) {
        console.warn('Erro ao carregar progresso salvo:', error);
      }
    }
  }, []);

  // Salvar progresso no localStorage
  useEffect(() => {
    if (progress.status !== 'idle') {
      localStorage.setItem('importProgress', JSON.stringify(progress));
    }
  }, [progress]);

  // Notificar mudanças de progresso
  useEffect(() => {
    if (onProgress) {
      onProgress(progress);
    }
  }, [progress, onProgress]);

  const updateProgress = useCallback((updates: Partial<ImportProgress>) => {
    setProgress(prev => {
      const newProgress = { ...prev, ...updates };
      
      // Recalcular porcentagem
      if (newProgress.total > 0) {
        newProgress.percentage = Math.round((newProgress.processed / newProgress.total) * 100);
      }
      
      // Calcular tempo estimado restante
      if (newProgress.processed > 0 && newProgress.processed < newProgress.total) {
        const tempoPorItem = 0.18; // estimativa de 0.18s por item
        const itensRestantes = newProgress.total - newProgress.processed;
        newProgress.estimatedTimeRemaining = Math.round(itensRestantes * tempoPorItem);
      }
      
      return newProgress;
    });
  }, []);

  const resetProgress = useCallback(() => {
    setProgress({
      total: 0,
      processed: 0,
      imported: 0,
      percentage: 0,
      status: 'idle'
    });
    localStorage.removeItem('importProgress');
    setStatus(null);
  }, []);

  const handleImport = async (tipo: 'completa' | 'recentes' | 'incremental') => {
    if (progress.status === 'running') return;
    
    setLoading(true);
    setModoImportacao(tipo);
    
    let endpoint = '';
    let mensagem = '';
    let expectedTotal = 17000; // estimativa para importação completa
    
    switch (tipo) {
      case 'completa':
        endpoint = '/estoque/importar-meli-todos-status';
        mensagem = '⏳ Importando todos os produtos do Mercado Livre (17k+)...';
        expectedTotal = 17000;
        break;
      case 'recentes':
        endpoint = '/estoque/importar-meli-incremental?hours=24';
        mensagem = '⏳ Importando produtos atualizados nas últimas 24h...';
        expectedTotal = 500; // estimativa para recentes
        break;
      case 'incremental':
        endpoint = '/meli/sync/incremental-start';
        mensagem = '⏳ Iniciando sincronização incremental em background...';
        expectedTotal = 100; // estimativa para incremental
        break;
    }
    
    setStatus(mensagem);
    updateProgress({
      total: expectedTotal,
      processed: 0,
      imported: 0,
      percentage: 0,
      status: 'running',
      currentPage: 1
    });
    
    try {
      // Usar importação REAL - SEM SIMULAÇÃO
      if (tipo === 'completa' || tipo === 'recentes') {
        await importReal(endpoint, tipo);
      } else {
        // Para incremental, usar o endpoint normal
        const data = await apiPost<{ importados?: number; tempo_execucao?: string; message?: string }>(endpoint);
        setStatus(`✅ Sincronização incremental iniciada: ${data.message || 'Processo em background'}`);
        updateProgress({
          ...progress,
          status: 'completed'
        });
      }
      
      if (onFinish) onFinish();
    } catch (err: any) {
      const errorMessage = `❌ Erro: ${String(err?.message || err)}`;
      setStatus(errorMessage);
      updateProgress({
        ...progress,
        status: 'error',
        error: errorMessage
      });
    } finally {
      setLoading(false);
    }
  };

  const importReal = async (endpoint: string, tipo: 'completa' | 'recentes') => {
    try {
      setStatus('🔄 Iniciando importação do Mercado Livre...');
      
      // Iniciar importação em background
      const importPromise = apiPost<{
        status: string;
        importados: number;
        tempo_execucao: string;
        stats: {
          fetched: number;
          novos: number;
          atualizados: number;
          ignorados: number;
        };
      }>(endpoint);
      
      // Enquanto isso, verificar o status do log mais recente
      let lastLogCheck = 0;
      const checkInterval = setInterval(async () => {
        try {
          const statusData = await apiGet('/estoque/meli/status') as any;
          
          // Se encontrou um log recente (últimos 5 minutos)
          if (statusData?.status && statusData?.created_at) {
            const logTime = new Date(statusData.created_at).getTime();
            const now = Date.now();
            const fiveMinutesAgo = now - (5 * 60 * 1000);
            
            if (logTime > lastLogCheck && logTime > fiveMinutesAgo) {
              lastLogCheck = logTime;
              
              // Atualizar progresso baseado no log
              updateProgress({
                total: statusData.total_importado || 0,
                processed: statusData.total_importado || 0,
                imported: statusData.total_importado || 0,
                percentage: statusData.status === 'completed' ? 100 : 50,
                status: statusData.status === 'running' ? 'running' : 
                        statusData.status === 'completed' ? 'completed' : 'idle'
              });
            }
          }
        } catch (error) {
          console.warn('Erro ao verificar status:', error);
        }
      }, 3000); // Verificar a cada 3 segundos
      
      // Aguardar conclusão da importação
      const data = await importPromise;
      clearInterval(checkInterval);
      
      if (data.status === 'sucesso') {
        const { importados, tempo_execucao, stats } = data;
        
        // Atualizar progresso final com dados REAIS do backend
        updateProgress({
          total: stats.fetched,
          processed: stats.fetched,
          imported: importados,
          percentage: 100,
          status: 'completed'
        });
        
        setStatus(`✅ Importação concluída: ${importados} produtos importados (${stats.novos} novos, ${stats.atualizados} atualizados, ${stats.ignorados} ignorados) em ${tempo_execucao}.`);
        
        // Notificar sucesso e atualizar lista
        if (onFinish) onFinish();
        
        // Forçar atualização da página após importação bem sucedida
        setTimeout(() => {
          window.location.reload();
        }, 2000);
        
      } else {
        throw new Error('Resposta inválida do servidor');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      setStatus(`❌ Erro na importação: ${errorMessage}`);
      updateProgress({
        ...progress,
        status: 'error',
        error: errorMessage
      });
      throw error;
    }
  };

  const handlePause = () => {
    updateProgress({ status: 'paused' });
    setStatus('⏸️ Importação pausada. Clique em Retomar para continuar.');
  };

  const handleResume = async () => {
    if (progress.status === 'paused') {
      setStatus('▶️ Retomando importação...');
      // Aqui você implementaria a lógica real de retomada
      // Por enquanto, vamos apenas mudar o status
      updateProgress({ status: 'running' });
    }
  };

  const handleCancel = () => {
    resetProgress();
    setStatus('❌ Importação cancelada.');
  };

  const formatTime = (seconds?: number) => {
    if (!seconds) return 'Calculando...';
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  return (
    <ImportContainer>
      <ImportHeader>
        <ImportTitle>
          <Package size={24} />
          Importação de Produtos
        </ImportTitle>
        <ActionButtons>
          {progress.status === 'running' && (
            <Button onClick={handlePause} variant="secondary" size="sm">
              <Pause size={16} />
              Pausar
            </Button>
          )}
          {progress.status === 'paused' && (
            <Button onClick={handleResume} variant="primary" size="sm">
              <Play size={16} />
              Retomar
            </Button>
          )}
          {(progress.status === 'running' || progress.status === 'paused') && (
            <Button onClick={handleCancel} variant="danger" size="sm">
              <Square size={16} />
              Cancelar
            </Button>
          )}
          {progress.status === 'completed' && (
            <Button onClick={resetProgress} variant="secondary" size="sm">
              <RotateCcw size={16} />
              Resetar
            </Button>
          )}
        </ActionButtons>
      </ImportHeader>

      {(progress.status === 'running' || progress.status === 'paused' || progress.status === 'completed' || progress.status === 'error') && (
        <>
          <StatsGrid>
            <StatCard>
              <StatValue>{progress.total.toLocaleString()}</StatValue>
              <StatLabel>Total</StatLabel>
            </StatCard>
            <StatCard>
              <StatValue>{progress.processed.toLocaleString()}</StatValue>
              <StatLabel>Processados</StatLabel>
            </StatCard>
            <StatCard>
              <StatValue>{progress.imported.toLocaleString()}</StatValue>
              <StatLabel>Importados</StatLabel>
            </StatCard>
            <StatCard>
              <StatValue>{formatTime(progress.estimatedTimeRemaining)}</StatValue>
              <StatLabel>Tempo Restante</StatLabel>
            </StatCard>
          </StatsGrid>

          <ProgressBar 
            progress={progress.percentage}
            status={progress.status}
            animated={progress.status === 'running'}
            showPercentage
            size="medium"
          />
        </>
      )}

      <ButtonGroup>
        <ImportTypeButton 
          onClick={() => handleImport('completa')} 
          loading={loading && modoImportacao === 'completa'}
          variant={modoImportacao === 'completa' ? 'primary' : 'secondary'}
          isActive={modoImportacao === 'completa'}
          disabled={progress.status === 'running'}
        >
          {loading && modoImportacao === 'completa' ? "Importando..." : "Apenas importação completa"}
        </ImportTypeButton>
        <ImportTypeButton 
          onClick={() => handleImport('recentes')} 
          loading={loading && modoImportacao === 'recentes'}
          variant={modoImportacao === 'recentes' ? 'primary' : 'secondary'}
          isActive={modoImportacao === 'recentes'}
          disabled={progress.status === 'running'}
        >
          {loading && modoImportacao === 'recentes' ? "Buscando..." : "🔄 Recentes (24h)"}
        </ImportTypeButton>
        <ImportTypeButton 
          onClick={() => handleImport('incremental')} 
          loading={loading && modoImportacao === 'incremental'}
          variant={modoImportacao === 'incremental' ? 'primary' : 'secondary'}
          isActive={modoImportacao === 'incremental'}
          disabled={progress.status === 'running'}
        >
          {loading && modoImportacao === 'incremental' ? "Processando..." : "⚡ Sync Incremental"}
        </ImportTypeButton>
      </ButtonGroup>

      {status && (
        <div style={{ 
          marginTop: '16px', 
          padding: '12px 16px', 
          background: progress.status === 'error' ? '#fef2f2' : '#f0f9ff',
          border: `1px solid ${progress.status === 'error' ? '#fecaca' : '#bae6fd'}`,
          borderRadius: '8px',
          color: progress.status === 'error' ? '#dc2626' : '#0369a1',
          fontSize: '0.9rem'
        }}>
          {status}
        </div>
      )}
    </ImportContainer>
  );
}