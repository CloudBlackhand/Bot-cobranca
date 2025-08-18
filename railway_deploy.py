#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Deploy Script - Claudia Cobranças
Script otimizado para deploy no Railway com fallback para Playwright
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_railway_environment():
    """Verificar se estamos rodando no Railway"""
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    railway_deploy = os.getenv('RAILWAY_DEPLOY', 'False') == 'True'
    
    if railway_env or railway_deploy:
        logger.info("🚂 Ambiente Railway detectado")
        return True
    
    logger.info("💻 Ambiente local detectado")
    return False

def install_dependencies():
    """Instalar dependências Python necessárias"""
    logger.info("📦 Instalando dependências Python...")
    
    try:
        # Instalar dependências básicas primeiro
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements_minimal.txt"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Erro ao instalar dependências mínimas: {result.stderr}")
            return False
            
        logger.info("✅ Dependências mínimas instaladas")
        
        # Tentar instalar dependências completas
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.warning(f"⚠️ Algumas dependências não foram instaladas: {result.stderr}")
        else:
            logger.info("✅ Todas as dependências instaladas")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao instalar dependências: {e}")
        return False

def try_install_playwright():
    """Tentar instalar Playwright (opcional)"""
    logger.info("🎭 Tentando instalar Playwright...")
    
    try:
        # Verificar se Playwright já está instalado
        import playwright
        logger.info("✅ Playwright já está instalado")
        
        # Tentar instalar navegadores
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            logger.info("✅ Navegador Chromium instalado")
            return True
        else:
            logger.warning("⚠️ Falha ao instalar navegador Chromium")
            return False
            
    except ImportError:
        logger.warning("⚠️ Playwright não disponível - funcionalidades limitadas")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Erro ao configurar Playwright: {e}")
        return False

def create_directories():
    """Criar diretórios necessários"""
    logger.info("📁 Criando diretórios...")
    
    directories = [
        "uploads",
        "faturas",
        "web/static",
        "logs",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Diretório {directory} criado/verificado")

def set_environment_variables():
    """Configurar variáveis de ambiente para Railway"""
    logger.info("🔧 Configurando variáveis de ambiente...")
    
    # Configurações para Railway
    os.environ['RAILWAY_DEPLOY'] = 'True'
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/tmp/playwright-browsers'
    os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '0'
    
    # Configurações de performance
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    logger.info("✅ Variáveis de ambiente configuradas")

def start_application():
    """Iniciar aplicação FastAPI"""
    port = os.getenv("PORT", "8000")
    host = "0.0.0.0"
    
    logger.info(f"🚀 Iniciando aplicação na porta {port}...")
    
    # Comando para iniciar o servidor
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app:app",
        "--host", host,
        "--port", port,
        "--log-level", "info",
        "--timeout-keep-alive", "75",
        "--workers", "1"
    ]
    
    if check_railway_environment():
        # Configurações específicas para Railway
        cmd.extend([
            "--limit-concurrency", "10",
            "--limit-max-requests", "1000"
        ])
    
    logger.info(f"🎯 Comando: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro ao iniciar aplicação: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Aplicação interrompida")
        sys.exit(0)

def main():
    """Função principal"""
    logger.info("=" * 50)
    logger.info("🚀 CLAUDIA COBRANÇAS - RAILWAY DEPLOY")
    logger.info("=" * 50)
    
    # Verificar ambiente
    is_railway = check_railway_environment()
    
    # Configurar variáveis de ambiente
    set_environment_variables()
    
    # Criar diretórios
    create_directories()
    
    # Instalar dependências
    if not install_dependencies():
        logger.error("❌ Falha ao instalar dependências críticas")
        sys.exit(1)
    
    # Tentar instalar Playwright (opcional)
    if is_railway:
        logger.info("🎭 Playwright será configurado sob demanda no Railway")
    else:
        try_install_playwright()
    
    # Iniciar aplicação
    start_application()

if __name__ == "__main__":
    main()