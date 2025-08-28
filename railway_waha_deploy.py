#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Deploy do WAHA no Railway
Facilita o deploy e configuração do WAHA como serviço separado
"""

import os
import sys
import json
import subprocess
import time
import requests
from typing import Dict, Any, Optional

class RailwayWAHADeploy:
    """Gerenciador de deploy do WAHA no Railway"""
    
    def __init__(self):
        self.railway_token = os.getenv('RAILWAY_TOKEN')
        self.project_id = os.getenv('RAILWAY_PROJECT_ID')
        
    def check_railway_cli(self) -> bool:
        """Verifica se o Railway CLI está instalado"""
        try:
            result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Railway CLI está instalado")
                return True
        except FileNotFoundError:
            print("❌ Railway CLI não está instalado")
            print("📦 Instale com: npm install -g @railway/cli")
        return False
    
    def create_waha_service(self) -> bool:
        """Cria um novo serviço para o WAHA no Railway"""
        print("\n🚀 Criando serviço WAHA no Railway...")
        
        # Cria o arquivo de configuração do WAHA
        waha_config = {
            "build": {
                "builder": "dockerfile",
                "dockerfilePath": "Dockerfile.waha"
            },
            "deploy": {
                "startCommand": "npm start",
                "healthcheckPath": "/api/health",
                "healthcheckTimeout": 300,
                "restartPolicyType": "on_failure",
                "restartPolicyMaxRetries": 10
            }
        }
        
        # Salva configuração
        with open('railway.waha.json', 'w') as f:
            json.dump(waha_config, f, indent=2)
        
        print("📝 Configuração do WAHA criada")
        return True
    
    def create_waha_dockerfile(self) -> bool:
        """Cria o Dockerfile para o WAHA"""
        dockerfile_content = """# WAHA Dockerfile para Railway
FROM devlikeapro/waha:latest

# Configurações do ambiente
ENV NODE_ENV=production
ENV PORT=3000

# Expõe a porta
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:3000/api/health || exit 1

# Comando de inicialização padrão do WAHA
CMD ["npm", "start"]
"""
        
        with open('Dockerfile.waha', 'w') as f:
            f.write(dockerfile_content)
        
        print("📦 Dockerfile do WAHA criado")
        return True
    
    def get_env_variables(self) -> Dict[str, str]:
        """Obtém as variáveis de ambiente necessárias"""
        claudia_url = input("🌐 Digite a URL da sua aplicação Claudia no Railway (ex: https://claudia.railway.app): ").strip()
        api_key = input("🔐 Digite uma chave de API para o WAHA (deixe vazio para sem autenticação): ").strip()
        
        env_vars = {
            "NODE_ENV": "production",
            "PORT": "3000",
            "WAHA_BASE_URL": "https://waha.railway.app",  # Será substituído pela URL real
            "WAHA_DEFAULT_SESSION_NAME": "claudia-cobrancas",
            "WAHA_SESSIONS_ENABLED": "true",
            "WAHA_WEBHOOK_URL": f"{claudia_url}/webhook",
            "WAHA_WEBHOOK_EVENTS": '["message", "message.any", "state.change"]',
            "WAHA_LOG_LEVEL": "info",
            "WAHA_HEALTHCHECK_ENABLED": "true",
            "WAHA_HEALTHCHECK_INTERVAL": "30000"
        }
        
        if api_key:
            env_vars["WAHA_API_KEY"] = api_key
        
        return env_vars
    
    def create_env_file(self, env_vars: Dict[str, str]) -> bool:
        """Cria arquivo de variáveis de ambiente para o Railway"""
        with open('.env.waha', 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        print("📋 Arquivo de variáveis de ambiente criado")
        return True
    
    def deploy_instructions(self) -> None:
        """Mostra instruções para deploy manual"""
        print("\n" + "="*60)
        print("📚 INSTRUÇÕES PARA DEPLOY DO WAHA NO RAILWAY")
        print("="*60)
        
        print("""
1️⃣ CRIAR NOVO SERVIÇO NO RAILWAY:
   - Acesse: https://railway.app
   - No seu projeto, clique em "New Service"
   - Escolha "Empty Service"
   - Nomeie como "waha" ou "whatsapp-api"

2️⃣ CONFIGURAR O SERVIÇO:
   - Vá em Settings > Source
   - Conecte ao GitHub (mesmo repositório)
   - OU use "railway up" no terminal

3️⃣ CONFIGURAR VARIÁVEIS DE AMBIENTE:
   - Vá em Variables
   - Adicione as seguintes variáveis:
   
   NODE_ENV=production
   PORT=3000
   WAHA_BASE_URL=<URL_DO_SEU_WAHA_NO_RAILWAY>
   WAHA_DEFAULT_SESSION_NAME=claudia-cobrancas
   WAHA_SESSIONS_ENABLED=true
   WAHA_WEBHOOK_URL=<URL_DA_CLAUDIA>/webhook
   WAHA_LOG_LEVEL=info
   WAHA_API_KEY=<SUA_CHAVE_SECRETA> (opcional)

4️⃣ CONFIGURAR BUILD:
   - Em Settings > Build
   - Dockerfile Path: Dockerfile.waha
   - OU use Docker Image: devlikeapro/waha:latest

5️⃣ DEPLOY:
   - Clique em "Deploy"
   - Aguarde o build e deploy

6️⃣ CONFIGURAR CLAUDIA:
   - No serviço da Claudia, adicione:
   WAHA_URL=<URL_DO_WAHA_NO_RAILWAY>
   WAHA_API_KEY=<MESMA_CHAVE_DO_PASSO_3> (se configurou)

7️⃣ TESTAR:
   - Acesse: <URL_DO_WAHA>/api/health
   - Execute: python waha_setup.py --url <URL_DO_WAHA>
""")
        
        print("\n" + "="*60)
        print("💡 DICAS IMPORTANTES:")
        print("="*60)
        print("""
- O WAHA precisa rodar como serviço SEPARADO da Claudia
- Cada serviço terá sua própria URL no Railway
- O WAHA usa bastante memória (~512MB mínimo)
- Considere usar um plano pago para estabilidade
- Configure health checks para auto-restart
- Use volumes para persistir sessões do WhatsApp
""")
    
    def create_deployment_script(self) -> None:
        """Cria script bash para facilitar o deploy"""
        script_content = """#!/bin/bash
# Script de deploy do WAHA no Railway

echo "🚀 Iniciando deploy do WAHA no Railway..."

# Verifica se o Railway CLI está instalado
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI não encontrado!"
    echo "📦 Instale com: npm install -g @railway/cli"
    exit 1
fi

# Login no Railway
echo "🔐 Fazendo login no Railway..."
railway login

# Cria novo serviço
echo "📦 Criando serviço WAHA..."
railway up -d

# Configura variáveis de ambiente
echo "⚙️ Configurando variáveis de ambiente..."
railway variables set NODE_ENV=production
railway variables set PORT=3000
railway variables set WAHA_DEFAULT_SESSION_NAME=claudia-cobrancas
railway variables set WAHA_SESSIONS_ENABLED=true
railway variables set WAHA_LOG_LEVEL=info

echo "✅ Deploy iniciado! Verifique o painel do Railway para acompanhar."
echo "🌐 Acesse: https://railway.app/dashboard"
"""
        
        with open('deploy_waha.sh', 'w') as f:
            f.write(script_content)
        
        os.chmod('deploy_waha.sh', 0o755)
        print("📜 Script de deploy criado: deploy_waha.sh")
    
    def run(self) -> None:
        """Executa o processo de configuração"""
        print("\n🤖 CONFIGURADOR DO WAHA PARA RAILWAY")
        print("="*60)
        
        # Verifica Railway CLI
        if not self.check_railway_cli():
            print("\n⚠️ Instale o Railway CLI primeiro!")
            print("📦 npm install -g @railway/cli")
            print("🔗 Mais info: https://docs.railway.app/develop/cli")
            return
        
        # Cria arquivos necessários
        self.create_waha_dockerfile()
        self.create_waha_service()
        
        # Obtém configurações
        print("\n📝 Configuração do WAHA:")
        env_vars = self.get_env_variables()
        self.create_env_file(env_vars)
        
        # Cria script de deploy
        self.create_deployment_script()
        
        # Mostra instruções
        self.deploy_instructions()
        
        print("\n✅ Configuração concluída!")
        print("📁 Arquivos criados:")
        print("   - Dockerfile.waha (Dockerfile do WAHA)")
        print("   - railway.waha.json (Configuração do Railway)")
        print("   - .env.waha (Variáveis de ambiente)")
        print("   - deploy_waha.sh (Script de deploy)")
        print("\n🚀 Próximos passos:")
        print("   1. Execute: ./deploy_waha.sh")
        print("   2. OU siga as instruções manuais acima")


def main():
    """Função principal"""
    deployer = RailwayWAHADeploy()
    deployer.run()


if __name__ == "__main__":
    main()