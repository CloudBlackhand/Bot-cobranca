# 🚀 COMO FAZER FUNCIONAR NO RAILWAY - GUIA RÁPIDO

## ⚠️ IMPORTANTE: O Railway NÃO suporta o WAHA no mesmo serviço!

O WAHA (WhatsApp HTTP API) precisa rodar **SEPARADAMENTE** da aplicação Claudia. Você tem 3 opções:

---

## 📌 Opção 1: MAIS FÁCIL - Teste Local Primeiro

```bash
# 1. Instale Docker Desktop
# 2. Execute:
./start_waha.sh

# 3. Escolha opção 1 (Desenvolvimento Local)
# 4. O sistema vai rodar com WAHA funcionando!
```

---

## 📌 Opção 2: RECOMENDADA - Railway com 2 Serviços

### Passo 1: Deploy do WAHA
1. Acesse: https://railway.app
2. Crie um **NOVO PROJETO**
3. New Service > Docker Image
4. Use a imagem: `devlikeapro/waha:latest`
5. Configure as variáveis:
   ```
   NODE_ENV=production
   PORT=3000
   WAHA_DEFAULT_SESSION_NAME=claudia-cobrancas
   ```
6. Deploy e anote a URL (ex: `https://waha-xxx.railway.app`)

### Passo 2: Deploy da Claudia
1. No **MESMO PROJETO**, crie outro serviço
2. Conecte seu GitHub com este repositório
3. Configure as variáveis:
   ```
   RAILWAY_DEPLOY=True
   WAHA_URL=https://waha-xxx.railway.app  (URL do passo 1)
   ```
4. Deploy!

### Passo 3: Configure o WhatsApp
```bash
# No seu computador:
python waha_setup.py --url https://waha-xxx.railway.app
# Escaneie o QR Code com o WhatsApp
```

---

## 📌 Opção 3: ALTERNATIVA - Use Mock do WAHA

Se você só quer testar sem WhatsApp real:

1. No Railway, configure:
   ```
   USE_MOCK_WAHA=True
   ```
2. Deploy normalmente
3. O sistema vai simular o envio de mensagens

---

## 🆘 COMANDOS ÚTEIS

```bash
# Iniciar tudo localmente (mais fácil para testar)
./start_waha.sh

# Configurar para Railway
python railway_waha_deploy.py

# Configurar WhatsApp
python waha_setup.py

# Ver documentação completa
cat DEPLOY_COMPLETO.md
```

---

## ❓ PROBLEMAS COMUNS

### "WAHA não conecta"
- O WAHA precisa estar em um serviço SEPARADO
- Verifique se a URL do WAHA está correta nas variáveis

### "QR Code não aparece"
- Aguarde 30 segundos após o deploy
- Execute: `python waha_setup.py --url SUA_URL_WAHA`

### "Railway cobra caro"
- Use o plano Hobby ($5/mês) que dá para os 2 serviços
- Ou use alternativas gratuitas como Render.com

---

## 💡 DICA IMPORTANTE

**Teste LOCALMENTE primeiro!** É muito mais fácil configurar e testar tudo no seu computador antes de fazer deploy.

```bash
# Super simples:
docker-compose up -d
python waha_setup.py
# Pronto! Funcionando!
```

---

## 📞 PRECISA DE AJUDA?

1. Leia: `DEPLOY_COMPLETO.md` (documentação completa)
2. Execute: `./start_waha.sh` e escolha opção 4 (documentação)
3. Veja os logs: `docker-compose logs -f` (local) ou Railway dashboard

---

**🎯 RESUMO: O WAHA precisa rodar separado. Use Docker local para testar, depois faça 2 serviços no Railway.**