import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import get_settings
from app.services.mercadolivre_service import refresh_access_token

logger = logging.getLogger(__name__)

class TokenMonitor:
    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Inicia o monitoramento de tokens"""
        if self.running:
            logger.warning("TokenMonitor já está rodando")
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("TokenMonitor iniciado")
        
    async def stop(self):
        """Para o monitoramento de tokens"""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("TokenMonitor parado")
        
    async def _monitor_loop(self):
        """Loop principal de monitoramento"""
        while self.running:
            try:
                await self._check_and_refresh_token()
                # Aguarda 30 minutos antes da próxima verificação
                await asyncio.sleep(1800)  # 30 minutos
            except Exception as e:
                logger.error(f"Erro no monitoramento de tokens: {e}")
                # Em caso de erro, aguarda 5 minutos e tenta novamente
                await asyncio.sleep(300)
                
    async def _check_and_refresh_token(self):
        """Verifica e renova o token se necessário"""
        try:
            # Verifica se o token atual está perto de expirar
            if await self._should_refresh_token():
                logger.info("Token próximo de expirar, renovando...")
                access_token, refresh_token = refresh_access_token()
                
                if access_token and refresh_token:
                    logger.info("Token renovado com sucesso")
                    # Atualiza as configurações em memória
                    self.settings.ML_ACCESS_TOKEN = access_token
                    self.settings.ML_REFRESH_TOKEN = refresh_token
                else:
                    logger.error("Falha ao renovar token")
                    
        except Exception as e:
            logger.error(f"Erro ao verificar/renovar token: {e}")
            
    async def _should_refresh_token(self) -> bool:
        """Verifica se o token deve ser renovado"""
        # Se não houver refresh token, não podemos renovar
        if not self.settings.ML_REFRESH_TOKEN:
            return False
            
        # Verifica se o access token atual é válido
        if not self.settings.ML_ACCESS_TOKEN:
            return True
            
        # Aqui você pode adicionar lógica para verificar a expiração do token
        # Por enquanto, vamos renovar a cada 6 horas para garantir
        return True
        
    async def force_refresh(self) -> tuple[Optional[str], Optional[str]]:
        """Força a renovação do token"""
        logger.info("Forçando renovação de token")
        return refresh_access_token()

# Instância global do monitor
token_monitor = TokenMonitor()

async def start_token_monitor():
    """Inicia o monitoramento de tokens"""
    await token_monitor.start()
    
async def stop_token_monitor():
    """Para o monitoramento de tokens"""
    await token_monitor.stop()