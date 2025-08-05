#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Start Script - Claudia Cobranças
Script otimizado para inicialização na Railway
"""

import os
import sys
import subprocess
import time
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Função principal de inicialização"""
    print("🚂 Iniciando Claudia Cobranças na Railway...")
    print("🏢 Sistema oficial de cobrança da Desktop")
    print("🧠 Inteligência nível ChatGPT")
    print("🔐 Sistema de login com aprovação manual")
    print("💾 StorageManager com limite de 50MB")
    print("🚀 Otimizado para Railway")
    print()
    
    # Verificar e instalar dependências
    print("📦 Verificando dependências...")
    try:
        # Executar teste de dependências
        subprocess.run([sys.executable, "test_deps.py"], check=True, capture_output=True)
        print("✅ Todas as dependências OK")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no teste de dependências: {e}")
        print("🔄 Tentando importar dependências principais...")
        try:
            import fastapi
            import uvicorn
            import playwright
            print("✅ Dependências principais OK")
        except ImportError as e2:
            print(f"❌ Dependência faltando: {e2}")
            sys.exit(1)
    
    # Instalar e testar Playwright browsers
    print("🎭 Instalando e testando Playwright browsers...")
    try:
        # Instalação direta do Chromium
        print("📦 Instalando Chromium...")
        subprocess.run(["python", "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
        print("✅ Chromium instalado com sucesso")
        
        # Testar Playwright
        print("🧪 Testando Playwright...")
        subprocess.run(["python", "test_playwright.py"], check=True, capture_output=True)
        print("✅ Playwright testado e funcionando")
        
    except Exception as e:
        print(f"❌ Erro ao instalar Playwright: {e}")
        print("⚠️ Tentando método alternativo...")
        try:
            # Método alternativo
            subprocess.run(["python", "-m", "playwright", "install", "--with-deps"], check=True, capture_output=True)
            print("✅ Playwright instalado com dependências")
        except Exception as e2:
            print(f"❌ Erro definitivo: {e2}")
            print("⚠️ Continuando sem browsers...")
    
    # Verificar arquivos essenciais
    essential_files = [
        "app.py",
        "config.py", 
        "requirements.txt",
        "Procfile",
        "railway.toml"
    ]
    
    print("📁 Verificando arquivos essenciais...")
    for file in essential_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - FALTANDO!")
            sys.exit(1)
    
    print("✅ Todos os arquivos essenciais encontrados")
    print()
    
    # Iniciar aplicação
    print("🚀 Iniciando Claudia Cobranças...")
    print("🌐 Acesse: https://seu-app.railway.app")
    print("🔐 Login: /login")
    print("📊 Dashboard: /dashboard")
    print()
    
    # Comando de inicialização CORRIGIDO
    port = os.getenv("PORT", 8000)
    cmd = [
        "python", "-m", "uvicorn", 
        "app:app", 
        "--host", "0.0.0.0", 
        "--port", str(port)
    ]
    
    print(f"🎯 Comando: {' '.join(cmd)}")
    print("🚀 Iniciando servidor...")
    print()
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Parando Claudia Cobranças...")
    except Exception as e:
        print(f"❌ Erro ao iniciar: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()