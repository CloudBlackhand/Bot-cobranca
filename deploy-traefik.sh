#!/bin/bash
# Script de deploy com Traefik
# Claudia Cobranças - Sistema de Cobrança da Desktop

set -e

echo "🚀 Deploy da Claudia Cobranças com Traefik"
echo "=========================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker não está instalado!"
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose não está instalado!"
    exit 1
fi

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    if [ -f .env.traefik ]; then
        print_warning "Arquivo .env não encontrado. Copiando de .env.traefik..."
        cp .env.traefik .env
        print_warning "Por favor, edite o arquivo .env com suas configurações antes de continuar."
        print_warning "Especialmente:"
        echo "  - DOMAIN (seu domínio)"
        echo "  - ACME_EMAIL (seu email para SSL)"
        echo "  - TRAEFIK_DASHBOARD_AUTH (senha do dashboard)"
        echo ""
        read -p "Pressione ENTER depois de configurar o .env..."
    else
        print_error "Arquivo .env não encontrado!"
        exit 1
    fi
fi

# Criar diretórios necessários
print_success "Criando diretórios necessários..."
mkdir -p traefik/certs
mkdir -p uploads
mkdir -p faturas
mkdir -p web/static

# Definir permissões corretas
chmod 600 traefik/traefik.yml 2>/dev/null || true
chmod 600 traefik/dynamic/*.yml 2>/dev/null || true

# Verificar se o arquivo acme.json existe e tem as permissões corretas
if [ ! -f traefik/certs/acme.json ]; then
    touch traefik/certs/acme.json
    chmod 600 traefik/certs/acme.json
fi

# Parar containers antigos
print_warning "Parando containers antigos..."
docker-compose down 2>/dev/null || true

# Build da imagem
print_success "Construindo imagem Docker..."
docker-compose build --no-cache claudia

# Verificar modo de operação
echo ""
echo "Selecione o modo de operação:"
echo "1) Desenvolvimento (HTTP apenas)"
echo "2) Produção (HTTPS com Let's Encrypt)"
read -p "Escolha (1 ou 2): " mode

if [ "$mode" == "2" ]; then
    # Modo produção
    print_warning "Modo PRODUÇÃO selecionado"
    print_warning "Certifique-se de que:"
    echo "  - O domínio está apontando para este servidor"
    echo "  - As portas 80 e 443 estão abertas"
    echo "  - O email no .env está correto"
    read -p "Pressione ENTER para continuar..."
    
    # Atualizar traefik.yml para produção
    sed -i 's|caServer: https://acme-staging-v02.api.letsencrypt.org/directory|caServer: https://acme-v02.api.letsencrypt.org/directory|g' traefik/traefik.yml
else
    # Modo desenvolvimento
    print_warning "Modo DESENVOLVIMENTO selecionado"
    print_warning "Acessível em: http://localhost e http://claudia.localhost"
fi

# Iniciar containers
print_success "Iniciando containers..."
docker-compose up -d

# Aguardar containers iniciarem
print_warning "Aguardando containers iniciarem..."
sleep 10

# Verificar status dos containers
print_success "Status dos containers:"
docker-compose ps

# Verificar logs
print_success "Últimas linhas dos logs:"
docker-compose logs --tail=20

# Mostrar URLs de acesso
echo ""
echo "=========================================="
print_success "Deploy concluído!"
echo ""
echo "📌 URLs de acesso:"
if [ "$mode" == "2" ]; then
    echo "  - Aplicação: https://${DOMAIN:-claudia.localhost}"
    echo "  - Dashboard Traefik: https://${DOMAIN:-claudia.localhost}:8080"
else
    echo "  - Aplicação: http://localhost"
    echo "  - Aplicação (alt): http://claudia.localhost"
    echo "  - Dashboard Traefik: http://localhost:8080"
fi
echo ""
echo "📝 Comandos úteis:"
echo "  - Ver logs: docker-compose logs -f"
echo "  - Parar: docker-compose down"
echo "  - Reiniciar: docker-compose restart"
echo "  - Status: docker-compose ps"
echo ""
echo "🔍 Verificar health check:"
echo "  curl http://localhost/health"
echo ""
echo "=========================================="

# Verificar health check
sleep 5
if curl -f http://localhost/health &>/dev/null; then
    print_success "Health check OK! Sistema está funcionando."
else
    print_error "Health check falhou. Verifique os logs: docker-compose logs claudia"
fi