#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de importação lazy para módulos que dependem do Playwright
Permite que o sistema funcione mesmo sem o Playwright instalado
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Flag global para indicar se o Playwright está disponível
PLAYWRIGHT_AVAILABLE = False

# Tentar importar Playwright
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
    logger.info("✅ Playwright disponível")
except ImportError:
    logger.warning("⚠️ Playwright não disponível - funcionalidades limitadas")
    
    # Classes mock para quando o Playwright não estiver disponível
    class Browser:
        pass
    
    class Page:
        pass
    
    async def async_playwright():
        class MockPlaywright:
            async def start(self):
                raise NotImplementedError("Playwright não está instalado")
        return MockPlaywright()

def check_playwright() -> bool:
    """Verificar se o Playwright está disponível"""
    return PLAYWRIGHT_AVAILABLE

def get_playwright_status() -> dict:
    """Retornar status do Playwright"""
    return {
        "available": PLAYWRIGHT_AVAILABLE,
        "message": "Playwright disponível" if PLAYWRIGHT_AVAILABLE else "Playwright não instalado",
        "features": {
            "whatsapp": PLAYWRIGHT_AVAILABLE,
            "fatura_download": PLAYWRIGHT_AVAILABLE,
            "captcha_solver": PLAYWRIGHT_AVAILABLE
        }
    }

class LazyWhatsAppClient:
    """Cliente WhatsApp com carregamento lazy"""
    
    def __init__(self):
        self._client = None
        self.available = False
        
    def initialize(self):
        """Inicializar cliente se possível"""
        if PLAYWRIGHT_AVAILABLE:
            try:
                from .whatsapp_client import WhatsAppClient
                self._client = WhatsAppClient()
                self.available = True
                logger.info("✅ WhatsApp Client inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar WhatsApp Client: {e}")
                self.available = False
        else:
            logger.warning("⚠️ WhatsApp Client não disponível sem Playwright")
            self.available = False
    
    def __getattr__(self, name):
        """Proxy para métodos do cliente real"""
        if self._client:
            return getattr(self._client, name)
        else:
            def unavailable(*args, **kwargs):
                return {"error": "WhatsApp Client não disponível - Playwright não instalado"}
            return unavailable

class LazyFaturaDownloader:
    """Downloader de faturas com carregamento lazy"""
    
    def __init__(self, page=None):
        self._downloader = None
        self.available = False
        self.page = page
        
    def initialize(self):
        """Inicializar downloader se possível"""
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                from .fatura_downloader import FaturaDownloader
                self._downloader = FaturaDownloader(self.page)
                self.available = True
                logger.info("✅ Fatura Downloader inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Fatura Downloader: {e}")
                self.available = False
        else:
            logger.warning("⚠️ Fatura Downloader não disponível sem Playwright")
            self.available = False
    
    def __getattr__(self, name):
        """Proxy para métodos do downloader real"""
        if self._downloader:
            return getattr(self._downloader, name)
        else:
            async def unavailable(*args, **kwargs):
                return {"error": "Fatura Downloader não disponível - Playwright não instalado"}
            return unavailable

class LazyCaptchaSolver:
    """Solver de captcha com carregamento lazy"""
    
    def __init__(self, page=None):
        self._solver = None
        self.available = False
        self.page = page
        
    def initialize(self):
        """Inicializar solver se possível"""
        if PLAYWRIGHT_AVAILABLE:
            try:
                from .captcha_solver import CaptchaSolver
                self._solver = CaptchaSolver(self.page)
                self.available = True
                logger.info("✅ Captcha Solver inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Captcha Solver: {e}")
                self.available = False
        else:
            logger.warning("⚠️ Captcha Solver não disponível sem Playwright")
            self.available = False
    
    def __getattr__(self, name):
        """Proxy para métodos do solver real"""
        if self._solver:
            return getattr(self._solver, name)
        else:
            def unavailable(*args, **kwargs):
                return {"error": "Captcha Solver não disponível - Playwright não instalado"}
            return unavailable

# Função helper para obter informações do sistema
def get_system_capabilities():
    """Retornar capacidades do sistema"""
    return {
        "playwright": PLAYWRIGHT_AVAILABLE,
        "whatsapp": PLAYWRIGHT_AVAILABLE,
        "fatura_download": PLAYWRIGHT_AVAILABLE,
        "captcha_solver": PLAYWRIGHT_AVAILABLE,
        "excel_processing": True,  # Sempre disponível
        "conversation_engine": True,  # Sempre disponível
        "storage_manager": True  # Sempre disponível
    }