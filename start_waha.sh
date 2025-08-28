#!/bin/bash
# Script para iniciar o sistema com WAHA

echo "🤖 CLAUDIA COBRANÇAS - Sistema com WhatsApp"
echo "==========================================="
echo ""
echo "Escolha como deseja executar o sistema:"
echo ""
echo "1) 🏠 Desenvolvimento Local (Docker Compose)"
echo "2) 🚂 Preparar para Railway"
echo "3) 🔧 Configurar WAHA existente"
echo "4) 📚 Ver documentação"
echo ""
read -p "Escolha uma opção (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Iniciando ambiente local..."
        echo ""
        
        # Verifica se Docker está instalado
        if ! command -v docker &> /dev/null; then
            echo "❌ Docker não está instalado!"
            echo "📦 Instale em: https://docs.docker.com/get-docker/"
            exit 1
        fi
        
        # Verifica se docker-compose está instalado
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ Docker Compose não está instalado!"
            echo "📦 Instale em: https://docs.docker.com/compose/install/"
            exit 1
        fi
        
        # Cria arquivo .env se não existir
        if [ ! -f .env ]; then
            echo "📝 Criando arquivo .env..."
            cp .env.example .env
            echo "⚠️  Configure o arquivo .env com suas variáveis!"
            echo ""
        fi
        
        # Inicia os serviços
        echo "🔄 Iniciando serviços..."
        docker-compose up -d
        
        # Aguarda serviços iniciarem
        echo "⏳ Aguardando serviços iniciarem..."
        sleep 10
        
        # Verifica status
        echo ""
        echo "📊 Status dos serviços:"
        docker-compose ps
        
        echo ""
        echo "✅ Serviços iniciados!"
        echo ""
        echo "📱 Configure o WhatsApp:"
        echo "   python waha_setup.py"
        echo ""
        echo "🌐 Acesse:"
        echo "   - Claudia: http://localhost:8000"
        echo "   - WAHA: http://localhost:3000"
        echo ""
        echo "📋 Ver logs: docker-compose logs -f"
        echo "🛑 Parar: docker-compose down"
        ;;
        
    2)
        echo ""
        echo "🚂 Preparando para deploy no Railway..."
        echo ""
        
        # Executa script de preparação
        python railway_waha_deploy.py
        ;;
        
    3)
        echo ""
        echo "🔧 Configuração do WAHA..."
        echo ""
        read -p "Digite a URL do WAHA (ex: http://localhost:3000): " waha_url
        
        # Executa setup
        python waha_setup.py --url "$waha_url"
        ;;
        
    4)
        echo ""
        echo "📚 Abrindo documentação..."
        echo ""
        
        # Tenta abrir no navegador
        if command -v xdg-open &> /dev/null; then
            xdg-open DEPLOY_COMPLETO.md
        elif command -v open &> /dev/null; then
            open DEPLOY_COMPLETO.md
        else
            cat DEPLOY_COMPLETO.md | less
        fi
        ;;
        
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac