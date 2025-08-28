# 🚀 GUIA COMPLETO DE DEPLOY - CLAUDIA COBRANÇAS COM WAHA

Este guia explica como fazer o sistema Claudia Cobranças funcionar com WhatsApp usando WAHA (WhatsApp HTTP API).

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Opção 1: Desenvolvimento Local](#opção-1-desenvolvimento-local)
3. [Opção 2: Deploy no Railway](#opção-2-deploy-no-railway)
4. [Opção 3: Deploy Alternativo](#opção-3-deploy-alternativo)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O sistema Claudia Cobranças precisa do WAHA para enviar mensagens via WhatsApp. O WAHA é uma API HTTP que conecta com o WhatsApp Web.

### Arquitetura do Sistema

```
┌─────────────────┐         ┌─────────────────┐
│                 │  HTTP   │                 │
│  Claudia App    │ <-----> │     WAHA        │
│   (Python)      │         │  (WhatsApp API) │
│                 │         │                 │
└─────────────────┘         └─────────────────┘
        ↑                           ↑
        │                           │
        │                           │
    [Cliente]                  [WhatsApp Web]
```

---

## 🏠 Opção 1: Desenvolvimento Local

### Pré-requisitos
- Docker e Docker Compose instalados
- Python 3.11+
- 2GB de RAM disponível

### Passo a Passo

#### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd claudia-cobrancas
```

#### 2. Configure as variáveis de ambiente
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env com suas configurações
nano .env
```

#### 3. Inicie os serviços com Docker Compose
```bash
# Inicia WAHA e Claudia
docker-compose up -d

# Verifica se está rodando
docker-compose ps

# Ver logs
docker-compose logs -f
```

#### 4. Configure o WhatsApp
```bash
# Execute o script de setup
python waha_setup.py

# Escaneie o QR Code que aparecerá
# Abra WhatsApp > Configurações > Dispositivos conectados > Conectar
```

#### 5. Teste o sistema
```bash
# Teste de envio de mensagem
python waha_setup.py --test 11999999999

# Acesse a aplicação
open http://localhost:8000
```

### 🛑 Parar os serviços
```bash
docker-compose down
```

---

## 🚂 Opção 2: Deploy no Railway

O Railway **NÃO suporta múltiplos serviços em um único projeto gratuito**. Você precisa criar **DOIS serviços separados**.

### Estrutura no Railway

```
Projeto Railway
├── Serviço 1: WAHA (WhatsApp API)
└── Serviço 2: Claudia (Aplicação Principal)
```

### 📦 Parte 1: Deploy do WAHA

#### Método A: Usando Template Pronto

1. **Acesse o template do WAHA:**
   ```
   https://railway.app/template/devlikeapro-waha
   ```

2. **Clique em "Deploy on Railway"**

3. **Configure as variáveis:**
   ```env
   NODE_ENV=production
   PORT=3000
   WAHA_DEFAULT_SESSION_NAME=claudia-cobrancas
   WAHA_WEBHOOK_URL=https://SEU-APP-CLAUDIA.railway.app/webhook
   WAHA_API_KEY=sua-chave-secreta-aqui
   ```

#### Método B: Deploy Manual

1. **Crie um novo projeto no Railway**
   ```bash
   # No terminal
   railway login
   railway init
   ```

2. **Crie o serviço WAHA**
   - No painel Railway, clique em "New Service"
   - Escolha "Docker Image"
   - Use a imagem: `devlikeapro/waha:latest`

3. **Configure as variáveis de ambiente no Railway:**
   ```env
   NODE_ENV=production
   PORT=3000
   WAHA_DEFAULT_SESSION_NAME=claudia-cobrancas
   WAHA_SESSIONS_ENABLED=true
   WAHA_WEBHOOK_URL=https://claudia-xxxxx.railway.app/webhook
   WAHA_LOG_LEVEL=info
   WAHA_API_KEY=sua-chave-secreta
   ```

4. **Deploy**
   - Clique em "Deploy"
   - Aguarde o serviço iniciar
   - Anote a URL gerada (ex: `https://waha-xxxxx.railway.app`)

### 📱 Parte 2: Deploy da Claudia

1. **No mesmo projeto, crie outro serviço**
   - Click em "New Service"
   - Conecte seu GitHub
   - Selecione o repositório da Claudia

2. **Configure as variáveis de ambiente:**
   ```env
   # Sistema
   RAILWAY_DEPLOY=True
   PORT=8000
   
   # WAHA
   WAHA_URL=https://waha-xxxxx.railway.app
   WAHA_API_KEY=sua-chave-secreta
   WAHA_INSTANCE_NAME=claudia-cobrancas
   WEBHOOK_URL=https://claudia-xxxxx.railway.app/webhook
   
   # Outras configurações
   LOG_LEVEL=INFO
   ENABLE_DETAILED_LOGS=False
   ```

3. **Configure o build:**
   - Build Command: (deixe vazio, usa Dockerfile)
   - Start Command: `python railway_startup.py`

4. **Deploy e teste**
   - Deploy acontece automaticamente
   - Acesse a URL da Claudia
   - Configure o WhatsApp

### 📲 Parte 3: Configurar WhatsApp

1. **Acesse o WAHA:**
   ```
   https://waha-xxxxx.railway.app
   ```

2. **Execute o setup:**
   ```bash
   # No seu computador local
   python waha_setup.py --url https://waha-xxxxx.railway.app
   ```

3. **Escaneie o QR Code**

4. **Teste o envio:**
   ```bash
   python waha_setup.py --test 11999999999 --url https://waha-xxxxx.railway.app
   ```

---

## 🔄 Opção 3: Deploy Alternativo

### Usando Render.com (Gratuito com limitações)

1. **Deploy do WAHA no Render:**
   - Crie conta em render.com
   - New > Web Service
   - Docker Image: `devlikeapro/waha:latest`
   - Configure variáveis similares ao Railway

2. **Deploy da Claudia no Railway:**
   - Configure `WAHA_URL` para apontar ao Render

### Usando Heroku (Pago)

1. **Crie dois apps no Heroku:**
   ```bash
   heroku create claudia-waha
   heroku create claudia-app
   ```

2. **Deploy com buildpacks:**
   ```bash
   # Para WAHA
   heroku container:push web -a claudia-waha
   heroku container:release web -a claudia-waha
   
   # Para Claudia
   git push heroku main
   ```

### Usando VPS (Digital Ocean, Linode, etc)

1. **Configure Docker no VPS:**
   ```bash
   # No servidor
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

2. **Clone e execute:**
   ```bash
   git clone <repositorio>
   cd claudia-cobrancas
   docker-compose up -d
   ```

3. **Configure Nginx (opcional):**
   ```nginx
   server {
       listen 80;
       server_name seu-dominio.com;
       
       location / {
           proxy_pass http://localhost:8000;
       }
       
       location /waha/ {
           proxy_pass http://localhost:3000/;
       }
   }
   ```

---

## 🔧 Troubleshooting

### Problema: WAHA não conecta

**Solução:**
```bash
# Verifique se está rodando
curl https://seu-waha.railway.app/api/health

# Verifique logs no Railway
railway logs -s waha

# Recrie a sessão
python waha_setup.py --url https://seu-waha.railway.app
```

### Problema: QR Code não aparece

**Solução:**
1. Aguarde 30 segundos após deploy
2. Verifique se a porta 3000 está exposta
3. Tente deletar e recriar a sessão

### Problema: Webhook não recebe mensagens

**Solução:**
```bash
# Teste o webhook manualmente
curl -X POST https://claudia.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "test"}'

# Verifique configuração do WAHA
curl https://waha.railway.app/api/sessions/claudia-cobrancas
```

### Problema: Railway cobra muito caro

**Solução:**
1. Use sleep/wake automático
2. Configure auto-scaling
3. Considere alternativas como Render ou VPS
4. Otimize uso de memória

### Problema: Sessão do WhatsApp desconecta

**Solução:**
1. Configure auto-reconnect no WAHA
2. Use volumes para persistir sessão
3. Configure health checks

---

## 📊 Monitoramento

### Verificar status:
```bash
# Status do WAHA
curl https://waha.railway.app/api/health

# Status da sessão
curl https://waha.railway.app/api/sessions/claudia-cobrancas

# Logs
railway logs -s waha
railway logs -s claudia
```

### Métricas importantes:
- CPU: < 50% uso médio
- RAM: < 512MB para WAHA
- Uptime: > 99%
- Response time: < 2s

---

## 💰 Custos Estimados

### Railway (Hobby Plan - $5/mês):
- WAHA: ~$2-3/mês
- Claudia: ~$2-3/mês
- Total: ~$5/mês

### Alternativas Gratuitas:
- Render.com: 750h/mês grátis
- Fly.io: 3 VMs grátis
- Oracle Cloud: Always Free tier

### VPS (mais controle):
- Digital Ocean: $6/mês
- Linode: $5/mês
- Vultr: $6/mês

---

## ✅ Checklist de Deploy

- [ ] WAHA deployado e rodando
- [ ] Claudia deployada e rodando
- [ ] Variáveis de ambiente configuradas
- [ ] WhatsApp conectado (QR Code escaneado)
- [ ] Webhook configurado e testado
- [ ] Mensagem de teste enviada
- [ ] Health checks configurados
- [ ] Logs funcionando
- [ ] Backup da sessão configurado

---

## 🆘 Suporte

### Recursos úteis:
- [Documentação WAHA](https://waha.devlike.pro/)
- [Railway Docs](https://docs.railway.app/)
- [Docker Docs](https://docs.docker.com/)

### Comandos úteis:
```bash
# Desenvolvimento local
docker-compose up -d          # Iniciar
docker-compose logs -f         # Ver logs
docker-compose down           # Parar

# Railway
railway login                 # Login
railway up                    # Deploy
railway logs                  # Ver logs
railway variables set KEY=VAL # Configurar variável

# WAHA Setup
python waha_setup.py          # Setup completo
python waha_setup.py --qr     # Novo QR Code
python waha_setup.py --status # Ver status
```

---

## 📝 Notas Importantes

1. **WAHA é pesado**: Precisa de pelo menos 512MB RAM
2. **Sessões expiram**: Configure auto-reconnect
3. **QR Code único**: Cada sessão tem seu próprio QR
4. **Webhook é essencial**: Sem ele, não recebe mensagens
5. **API Key recomendada**: Para segurança em produção

---

**🎉 Pronto! Seu sistema Claudia Cobranças está configurado com WhatsApp!**