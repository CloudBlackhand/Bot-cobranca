# 🚀 Deploy com Traefik - Claudia Cobranças

Este documento explica como fazer o deploy da aplicação Claudia Cobranças usando Traefik como proxy reverso.

## 📋 Pré-requisitos

- Docker instalado (versão 20.10+)
- Docker Compose instalado (versão 2.0+)
- Portas 80, 443 e 8080 disponíveis
- Domínio configurado (para produção com HTTPS)

## 🛠️ Configuração Rápida

### 1. Configurar variáveis de ambiente

```bash
# Copiar arquivo de exemplo
cp .env.traefik .env

# Editar configurações
nano .env
```

**Configurações importantes:**

- `DOMAIN`: Seu domínio (ex: claudia.exemplo.com)
- `ACME_EMAIL`: Email para certificados SSL
- `TRAEFIK_DASHBOARD_AUTH`: Senha do dashboard (gerar com `htpasswd -nb admin senha`)

### 2. Deploy automático

```bash
# Executar script de deploy
./deploy-traefik.sh
```

O script irá:
- Verificar dependências
- Criar diretórios necessários
- Construir a imagem Docker
- Configurar Traefik
- Iniciar todos os serviços

## 🔧 Deploy Manual

### 1. Preparar ambiente

```bash
# Criar diretórios
mkdir -p traefik/certs uploads faturas web/static

# Criar arquivo para certificados
touch traefik/certs/acme.json
chmod 600 traefik/certs/acme.json
```

### 2. Construir e iniciar

```bash
# Build da aplicação
docker-compose build

# Iniciar serviços
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## 🌐 Acessando a Aplicação

### Desenvolvimento (HTTP)

- Aplicação: http://localhost ou http://claudia.localhost
- Dashboard Traefik: http://localhost:8080
- Health Check: http://localhost/health

### Produção (HTTPS)

- Aplicação: https://seu-dominio.com
- Dashboard Traefik: https://seu-dominio.com:8080 (protegido por senha)
- Health Check: https://seu-dominio.com/health

## 🔍 Verificação e Troubleshooting

### Verificar status dos containers

```bash
docker-compose ps
```

### Verificar logs

```bash
# Todos os logs
docker-compose logs -f

# Logs específicos
docker-compose logs -f claudia
docker-compose logs -f traefik
```

### Verificar health check

```bash
curl http://localhost/health
```

### Testar WebSocket

```javascript
// No console do navegador
const ws = new WebSocket('ws://localhost/ws/status');
ws.onmessage = (e) => console.log('WebSocket:', e.data);
```

## 🔒 Segurança

### Headers de Segurança

O Traefik adiciona automaticamente os seguintes headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (em HTTPS)

### Rate Limiting

Configurado para:
- 100 requisições por minuto em média
- Burst de até 50 requisições

### CORS

Configurado para aceitar apenas origens específicas definidas em `ALLOWED_ORIGINS`.

## 📊 Monitoramento

### Dashboard do Traefik

Acesse http://localhost:8080 para:
- Ver rotas configuradas
- Monitorar serviços
- Ver métricas
- Debugar problemas

### Métricas Prometheus

Disponível em http://localhost:8080/metrics

### Logs estruturados

```bash
# Ver apenas erros
docker-compose logs claudia | grep ERROR

# Ver requisições
docker-compose logs traefik | grep -E "GET|POST|PUT|DELETE"
```

## 🔄 Manutenção

### Atualizar aplicação

```bash
# Parar serviços
docker-compose down

# Atualizar código
git pull

# Reconstruir e reiniciar
docker-compose build
docker-compose up -d
```

### Backup

```bash
# Backup dos dados
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ faturas/

# Backup das configurações
tar -czf config-backup.tar.gz .env traefik/
```

### Limpar containers e volumes

```bash
# Parar e remover tudo
docker-compose down -v

# Limpar imagens não utilizadas
docker system prune -a
```

## 🚨 Problemas Comuns

### WebSocket não conecta

**Problema:** WebSocket retorna erro 404 ou não conecta

**Solução:**
1. Verificar se `BEHIND_PROXY=true` está configurado
2. Verificar labels do Traefik no docker-compose.yml
3. Verificar console do navegador para erros

### Certificado SSL não funciona

**Problema:** Navegador mostra erro de certificado

**Solução:**
1. Verificar se o domínio está apontando para o servidor
2. Verificar email em `ACME_EMAIL`
3. Verificar logs do Traefik: `docker-compose logs traefik | grep acme`
4. Para teste, usar staging do Let's Encrypt

### Health check falhando

**Problema:** Container reinicia constantemente

**Solução:**
1. Aumentar timeout no docker-compose.yml
2. Verificar logs: `docker-compose logs claudia`
3. Verificar se Playwright está instalado corretamente

### Erro de CORS

**Problema:** Requisições bloqueadas por CORS

**Solução:**
1. Adicionar origem em `ALLOWED_ORIGINS` no .env
2. Reiniciar containers: `docker-compose restart`

## 📚 Configurações Avançadas

### Múltiplas instâncias (Load Balancing)

```yaml
# docker-compose.yml
claudia:
  deploy:
    replicas: 3
```

### Cache com Redis

O Redis já está configurado no docker-compose.yml. Para usar:

```python
# No código Python
import redis
r = redis.Redis(host='redis', port=6379)
```

### Subpath deployment

Para rodar em subpath (ex: /app):

```bash
# .env
ROOT_PATH=/app
```

### Custom domain com SSL

1. Apontar DNS para o servidor
2. Configurar domínio no .env
3. Executar deploy em modo produção

## 🤝 Suporte

Para problemas ou dúvidas:
- Email: cobranca@desktop.com.br
- Logs: Sempre incluir logs completos ao reportar problemas

## 📄 Licença

Sistema proprietário da Desktop - Todos os direitos reservados.