import { apiGet, apiPost } from '@/lib/api';

export interface ImportProgress {
  total: number;
  processed: number;
  imported: number;
  skipped: number;
  errors: number;
  percentage: number;
  status: 'idle' | 'running' | 'paused' | 'error' | 'completed';
  message: string;
  startTime?: number;
  estimatedEndTime?: number;
  currentPage: number;
  totalPages: number;
}

export interface ImportResult {
  importados: number;
  tempo_execucao: string;
  fetched?: number;
  novos?: number;
  atualizados?: number;
  ignorados_sem_mudanca?: number;
  stats?: {
    fetched: number;
    novos: number;
    atualizados: number;
    ignorados_sem_mudanca: number;
  };
}

class ImportService {
  private progress: ImportProgress = {
    total: 0,
    processed: 0,
    imported: 0,
    skipped: 0,
    errors: 0,
    percentage: 0,
    status: 'idle',
    message: 'Pronto para importar',
    currentPage: 0,
    totalPages: 0,
  };

  private abortController: AbortController | null = null;
  private onProgressCallback: ((progress: ImportProgress) => void) | null = null;
  private resumeData: any = null;

  constructor() {
    this.loadResumeData();
  }

  private loadResumeData() {
    try {
      const saved = localStorage.getItem('import_resume_data');
      if (saved) {
        this.resumeData = JSON.parse(saved);
      }
    } catch (error) {
      console.warn('Erro ao carregar dados de retomada:', error);
      this.resumeData = null;
    }
  }

  private saveResumeData(data: any) {
    try {
      localStorage.setItem('import_resume_data', JSON.stringify(data));
    } catch (error) {
      console.warn('Erro ao salvar dados de retomada:', error);
    }
  }

  private clearResumeData() {
    try {
      localStorage.removeItem('import_resume_data');
      this.resumeData = null;
    } catch (error) {
      console.warn('Erro ao limpar dados de retomada:', error);
    }
  }

  private updateProgress(updates: Partial<ImportProgress>) {
    this.progress = { ...this.progress, ...updates };
    
    // Calcular porcentagem e estimativas
    if (this.progress.total > 0) {
      this.progress.percentage = Math.round((this.progress.processed / this.progress.total) * 100);
      
      if (this.progress.startTime && this.progress.processed > 0) {
        const elapsed = Date.now() - this.progress.startTime;
        const rate = this.progress.processed / elapsed;
        const remaining = this.progress.total - this.progress.processed;
        const estimatedRemaining = remaining / rate;
        this.progress.estimatedEndTime = Date.now() + estimatedRemaining;
      }
    }

    if (this.onProgressCallback) {
      this.onProgressCallback(this.progress);
    }
  }

  private async simulateProgress(endpoint: string, params: string = '') {
    try {
      this.updateProgress({
        status: 'running',
        message: 'Iniciando importação...',
        startTime: Date.now(),
        currentPage: 0,
      });

      // Primeiro, vamos descobrir o total
      this.updateProgress({
        message: 'Buscando total de produtos...',
      });

      // Simular progresso gradual
      const simulatePages = async () => {
        const totalPages = Math.ceil(this.progress.total / 50) || 100; // 50 produtos por página
        
        for (let page = 1; page <= totalPages; page++) {
          if (this.abortController?.signal.aborted) {
            throw new Error('Importação cancelada');
          }

          // Simular processamento de página
          await new Promise(resolve => setTimeout(resolve, 500)); // Simular delay
          
          const processed = page * 50;
          const imported = Math.floor(processed * 0.3); // Taxa de importação de 30%
          const skipped = processed - imported;
          
          this.updateProgress({
            processed,
            imported,
            skipped,
            currentPage: page,
            totalPages,
            message: `Processando página ${page} de ${totalPages}...`,
          });

          // Salvar dados para retomada
          this.saveResumeData({
            endpoint,
            params,
            currentPage: page,
            totalPages,
            progress: this.progress,
          });
        }
      };

      await simulatePages();

      // Agora executar a importação real
      this.updateProgress({
        message: 'Importando produtos do Mercado Livre...',
      });

      const result = await this.executeImport(endpoint, params);
      
      this.updateProgress({
        status: 'completed',
        message: `✅ Importação concluída: ${result.importados} produtos importados em ${result.tempo_execucao}`,
        imported: result.importados,
        percentage: 100,
      });

      this.clearResumeData();
      return result;

    } catch (error) {
      this.updateProgress({
        status: 'error',
        message: `❌ Erro: ${error instanceof Error ? error.message : 'Erro desconhecido'}`,
        errors: (this.progress.errors || 0) + 1,
      });
      throw error;
    }
  }

  private async executeImport(endpoint: string, params: string): Promise<ImportResult> {
    const url = `${endpoint}${params}`;
    
    try {
      const response = await apiPost<ImportResult>(url);
      return response;
    } catch (error) {
      console.error('Erro na importação:', error);
      throw error;
    }
  }

  // Métodos públicos
  onProgress(callback: (progress: ImportProgress) => void) {
    this.onProgressCallback = callback;
  }

  async importCompleta() {
    return this.simulateProgress('/estoque/importar-meli-todos-status', '?limit=50000');
  }

  async importRecentes(hours: number = 24) {
    return this.simulateProgress('/estoque/importar-meli-incremental', `?hours=${hours}`);
  }

  async importIncremental() {
    return this.simulateProgress('/estoque/importar-meli', '?limit=500&novos=true');
  }

  canResume(): boolean {
    return !!this.resumeData && this.resumeData.progress?.status !== 'completed';
  }

  async resume() {
    if (!this.canResume()) {
      throw new Error('Não há importação para retomar');
    }

    const { endpoint, params, progress } = this.resumeData;
    
    // Restaurar estado anterior
    this.updateProgress({
      ...progress,
      status: 'running',
      message: 'Retomando importação...',
    });

    return this.simulateProgress(endpoint, params);
  }

  pause() {
    if (this.abortController) {
      this.abortController.abort();
    }
    
    this.updateProgress({
      status: 'paused',
      message: '⏸️ Importação pausada',
    });
  }

  cancel() {
    if (this.abortController) {
      this.abortController.abort();
    }
    
    this.updateProgress({
      status: 'idle',
      message: '❌ Importação cancelada',
    });
    
    this.clearResumeData();
  }

  getProgress(): ImportProgress {
    return this.progress;
  }

  reset() {
    this.progress = {
      total: 0,
      processed: 0,
      imported: 0,
      skipped: 0,
      errors: 0,
      percentage: 0,
      status: 'idle',
      message: 'Pronto para importar',
      currentPage: 0,
      totalPages: 0,
    };
    
    this.clearResumeData();
    
    if (this.onProgressCallback) {
      this.onProgressCallback(this.progress);
    }
  }
}

// Exportar instância singleton
export const importService = new ImportService();