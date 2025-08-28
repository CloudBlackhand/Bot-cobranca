#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuração do WAHA para Claudia Cobranças
Facilita a inicialização e configuração do WAHA
"""

import os
import sys
import time
import json
import requests
import qrcode
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WAHASetup:
    """Gerenciador de configuração do WAHA"""
    
    def __init__(self, waha_url: str = None):
        self.waha_url = waha_url or os.getenv('WAHA_URL', 'http://localhost:3000')
        self.instance_name = os.getenv('WAHA_INSTANCE_NAME', 'claudia-cobrancas')
        self.webhook_url = os.getenv('WEBHOOK_URL', 'http://localhost:8000/webhook')
        self.api_key = os.getenv('WAHA_API_KEY', '')
        
    def check_health(self) -> bool:
        """Verifica se o WAHA está rodando"""
        try:
            response = requests.get(f"{self.waha_url}/api/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ WAHA está rodando e saudável")
                return True
        except Exception as e:
            logger.error(f"❌ WAHA não está acessível: {e}")
        return False
    
    def create_session(self) -> Dict[str, Any]:
        """Cria uma nova sessão no WAHA"""
        try:
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                
            payload = {
                "name": self.instance_name,
                "config": {
                    "webhook": {
                        "url": self.webhook_url,
                        "events": ["message", "message.any", "state.change"]
                    }
                }
            }
            
            response = requests.post(
                f"{self.waha_url}/api/sessions",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Sessão '{self.instance_name}' criada com sucesso")
                return response.json()
            else:
                logger.error(f"❌ Erro ao criar sessão: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar sessão: {e}")
            return {}
    
    def get_qr_code(self) -> Optional[str]:
        """Obtém o QR Code para autenticação"""
        try:
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                
            response = requests.get(
                f"{self.waha_url}/api/sessions/{self.instance_name}/auth/qr",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                qr_data = data.get('qr', '')
                
                if qr_data:
                    # Gera QR Code no terminal
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    
                    # Salva QR Code como imagem
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save('waha_qr.png')
                    
                    # Mostra no terminal
                    qr.print_ascii()
                    
                    logger.info("✅ QR Code gerado! Escaneie com o WhatsApp")
                    logger.info("📱 Abra o WhatsApp > Configurações > Dispositivos conectados > Conectar dispositivo")
                    logger.info("🖼️ QR Code salvo em: waha_qr.png")
                    
                    return qr_data
                else:
                    logger.info("ℹ️ Sessão já está autenticada ou aguardando QR")
                    
        except Exception as e:
            logger.error(f"❌ Erro ao obter QR Code: {e}")
        
        return None
    
    def check_session_status(self) -> Dict[str, Any]:
        """Verifica o status da sessão"""
        try:
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                
            response = requests.get(
                f"{self.waha_url}/api/sessions/{self.instance_name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                
                status_messages = {
                    'STARTING': '🔄 Sessão iniciando...',
                    'SCAN_QR_CODE': '📱 Aguardando escaneamento do QR Code',
                    'WORKING': '✅ Sessão conectada e funcionando!',
                    'FAILED': '❌ Sessão falhou',
                    'STOPPED': '⏹️ Sessão parada'
                }
                
                logger.info(status_messages.get(status, f"Status: {status}"))
                return data
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {e}")
            
        return {}
    
    def start_session(self) -> bool:
        """Inicia uma sessão existente"""
        try:
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                
            response = requests.post(
                f"{self.waha_url}/api/sessions/{self.instance_name}/start",
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info("✅ Sessão iniciada com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar sessão: {e}")
            
        return False
    
    def send_test_message(self, phone_number: str, message: str = None) -> bool:
        """Envia uma mensagem de teste"""
        try:
            if not message:
                message = "🤖 Teste do sistema Claudia Cobranças - WhatsApp funcionando!"
                
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                
            # Formata número (remove caracteres especiais)
            phone = ''.join(filter(str.isdigit, phone_number))
            if not phone.startswith('55'):
                phone = '55' + phone
                
            payload = {
                "chatId": f"{phone}@c.us",
                "text": message
            }
            
            response = requests.post(
                f"{self.waha_url}/api/sendText",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Mensagem enviada para {phone_number}")
                return True
            else:
                logger.error(f"❌ Erro ao enviar mensagem: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem: {e}")
            
        return False
    
    def setup_webhook(self) -> bool:
        """Configura o webhook para receber mensagens"""
        try:
            headers = {}
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                
            payload = {
                "url": self.webhook_url,
                "events": ["message", "message.any", "state.change", "group.join", "group.leave"]
            }
            
            response = requests.post(
                f"{self.waha_url}/api/sessions/{self.instance_name}/webhooks",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Webhook configurado: {self.webhook_url}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao configurar webhook: {e}")
            
        return False
    
    def full_setup(self) -> bool:
        """Executa o setup completo do WAHA"""
        logger.info("🚀 Iniciando configuração do WAHA...")
        
        # 1. Verifica saúde
        if not self.check_health():
            logger.error("❌ WAHA não está rodando. Execute: docker-compose up -d waha")
            return False
        
        # 2. Cria sessão
        session = self.create_session()
        if not session:
            logger.info("ℹ️ Tentando usar sessão existente...")
        
        # 3. Verifica status
        status = self.check_session_status()
        current_status = status.get('status', '')
        
        # 4. Se precisa QR Code
        if current_status == 'SCAN_QR_CODE':
            self.get_qr_code()
            
            # Aguarda autenticação
            logger.info("⏳ Aguardando autenticação...")
            for i in range(60):  # Aguarda até 60 segundos
                time.sleep(1)
                status = self.check_session_status()
                if status.get('status') == 'WORKING':
                    break
        
        # 5. Se está parada, inicia
        elif current_status == 'STOPPED':
            self.start_session()
            time.sleep(2)
            status = self.check_session_status()
        
        # 6. Configura webhook
        if status.get('status') == 'WORKING':
            self.setup_webhook()
            logger.info("✅ WAHA configurado com sucesso!")
            return True
        
        logger.error("❌ Não foi possível configurar o WAHA completamente")
        return False


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup do WAHA para Claudia Cobranças')
    parser.add_argument('--url', default='http://localhost:3000', help='URL do WAHA')
    parser.add_argument('--test', help='Número para enviar mensagem de teste (ex: 11999999999)')
    parser.add_argument('--status', action='store_true', help='Apenas verifica o status')
    parser.add_argument('--qr', action='store_true', help='Gera novo QR Code')
    
    args = parser.parse_args()
    
    setup = WAHASetup(args.url)
    
    if args.status:
        setup.check_health()
        setup.check_session_status()
    elif args.qr:
        setup.get_qr_code()
    elif args.test:
        if setup.check_health():
            status = setup.check_session_status()
            if status.get('status') == 'WORKING':
                setup.send_test_message(args.test)
            else:
                logger.error("❌ Sessão não está funcionando. Execute o setup primeiro.")
    else:
        setup.full_setup()


if __name__ == "__main__":
    main()