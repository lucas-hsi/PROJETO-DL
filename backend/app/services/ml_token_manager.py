"""
Sistema de Token Permanente para Mercado Livre
Solução definitiva para evitar renovações manuais frequentes
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MercadoLivreTokenManager:
    """
    Gerenciador de tokens com estratégias múltiplas:
    1. Client Credentials - Para leitura (sem refresh token)
    2. Authorization Code - Para escrita (com refresh token longo)
    3. Monitoramento ativo - Alerta antes da expiração
    """
    
    def __init__(self):
        self.client_id = os.getenv("ML_CLIENT_ID") or os.getenv("MERCADO_LIVRE_CLIENT_ID")
        self.client_secret = os.getenv("ML_CLIENT_SECRET") or os.getenv("MERCADO_LIVRE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("ML_REDIRECT_URI") or os.getenv("MERCADO_LIVRE_REDIRECT_URI")
        
        # Tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Client Credentials (para leitura)
        self.cc_access_token = None
        self.cc_token_expires_at = None
        
    def get_client_credentials_token(self) -> Optional[str]:
        """
        Obter token via Client Credentials - NÃO requer refresh token!
        Perfeito para operações de leitura como buscar produtos.
        """
        try:
            # Verificar se token ainda é válido
            if self.cc_access_token and self.cc_token_expires_at:
                if datetime.now() < self.cc_token_expires_at:
                    return self.cc_access_token
            
            # Solicitar novo token
            url = "https://api.mercadolibre.com/oauth/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.cc_access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 21600)  # 6 horas padrão
                self.cc_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"✅ Client Credentials token obtido! Expira em: {self.cc_token_expires_at}")
                return self.cc_access_token
            else:
                logger.error(f"❌ Erro ao obter Client Credentials token: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro no Client Credentials: {e}")
            return None
    
    def check_token_validity(self) -> Dict[str, Any]:
        """
        Verificar status dos tokens e tempo até expiração
        """
        now = datetime.now()
        
        status = {
            "cc_token_valid": False,
            "cc_token_expires_in": 0,
            "auth_token_valid": False,
            "auth_token_expires_in": 0,
            "needs_renewal": False,
            "urgent_renewal": False
        }
        
        # Client Credentials
        if self.cc_access_token and self.cc_token_expires_at:
            if now < self.cc_token_expires_at:
                status["cc_token_valid"] = True
                status["cc_token_expires_in"] = int((self.cc_token_expires_at - now).total_seconds() / 60)
        
        # Authorization Code (refresh token)
        if self.access_token and self.token_expires_at:
            if now < self.token_expires_at:
                status["auth_token_valid"] = True
                status["auth_token_expires_in"] = int((self.token_expires_at - now).total_seconds() / 60)
        
        # Verificar se precisa renovar (com 7 dias de antecedência)
        if self.token_expires_at:
            days_until_expiry = (self.token_expires_at - now).days
            if days_until_expiry <= 7:
                status["needs_renewal"] = True
            if days_until_expiry <= 1:
                status["urgent_renewal"] = True
        
        return status
    
    def get_best_token(self, operation_type: str = "read") -> Optional[str]:
        """
        Obter o melhor token para a operação:
        - "read": Usa Client Credentials (mais estável)
        - "write": Usa Authorization Code (usuário logado)
        """
        if operation_type == "read":
            # Para leitura, preferir Client Credentials
            token = self.get_client_credentials_token()
            if token:
                return token
            
            # Fallback para token do usuário
            if self.access_token and self.token_expires_at:
                if datetime.now() < self.token_expires_at:
                    return self.access_token
        
        elif operation_type == "write":
            # Para escrita, precisa do token do usuário
            if self.access_token and self.token_expires_at:
                if datetime.now() < self.token_expires_at:
                    return self.access_token
        
        return None
    
    def notify_renewal_needed(self):
        """
        Notificar que renovação será necessária em breve
        """
        status = self.check_token_validity()
        
        if status["urgent_renewal"]:
            logger.warning("🚨 URGENTE: Token expira em menos de 24h! Renove o quanto antes.")
            # Aqui poderia enviar email, notificação, etc.
            
        elif status["needs_renewal"]:
            logger.warning("⚠️ ATENÇÃO: Token expira em menos de 7 dias. Prepare a renovação.")
            # Aqui poderia enviar notificação preventiva
    
    def get_renewal_instructions(self) -> str:
        """
        Retornar instruções claras para renovação manual (mínima)
        """
        return """
        📋 INSTRUÇÕES PARA RENOVAÇÃO DO TOKEN (1x a cada 6 meses):
        
        1. Acesse: https://www.mercadolivre.com/jms/mlb/lgz/login?platform_id=ml&go=https://www.mercadolivre.com
        2. Faça login com a conta: {sua_conta_ml}
        3. Acesse: {redirect_uri}
        4. Copie o código TG que aparece na URL (ex: TG-1234567890abcdef)
        5. Envie o código para o sistema
        
        💡 DICA: Marque no calendário para renovar a cada 6 meses!
        
        🎯 Isso só é necessário para operações de ESCRITA (criar anúncios, etc.)
        Para LEITURA (buscar produtos), o sistema funciona automaticamente!
        """

# Instância global
ml_token_manager = MercadoLivreTokenManager()

def get_ml_token(operation_type: str = "read") -> Optional[str]:
    """
    Função helper para obter token facilmente
    """
    return ml_token_manager.get_best_token(operation_type)

def check_ml_token_status():
    """
    Função helper para verificar status dos tokens
    """
    return ml_token_manager.check_token_validity()

def notify_ml_token_renewal():
    """
    Função helper para notificar sobre renovação
    """
    return ml_token_manager.notify_renewal_needed()