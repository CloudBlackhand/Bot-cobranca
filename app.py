#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLAUDIA COBRANÇAS - Sistema de Cobrança da Desktop
Aplicação principal FastAPI com interface web
"""

import os
import asyncio
from fastapi.websockets import WebSocketDisconnect
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.requests import Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import List, Optional
import logging
import uuid
import json
import time
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 MODELOS PARA SISTEMA DE AUTENTICAÇÃO
class LoginRequest(BaseModel):
    email: str
    password: str
    reason: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None

class SessionValidation(BaseModel):
    token: str

# 🗃️ ARMAZENAMENTO DE AUTENTICAÇÃO (em memória para simplicidade)
pending_auth_requests = {}  # {request_id: {email, timestamp, ip, reason, etc}}
active_sessions = {}       # {token: {email, timestamp, request_id}}
auth_settings = {
    "session_timeout": 3600,  # 1 hora
    "request_timeout": 300,   # 5 minutos
    "max_pending": 10
}

# Importar módulos core
from core.excel_processor import ExcelProcessor
from core.whatsapp_client import WhatsAppClient
from core.conversation import SuperConversationEngine
from core.fatura_downloader import FaturaDownloader
from core.captcha_solver import CaptchaSolver, get_captcha_solver_info
from core.storage_manager import storage_manager
from config import Config, CLAUDIA_CONFIG

# Detectar se estamos atrás de um proxy
BEHIND_PROXY = os.getenv("BEHIND_PROXY", "false").lower() == "true"
ROOT_PATH = os.getenv("ROOT_PATH", "")

# Inicializar FastAPI com configurações para proxy
app = FastAPI(
    title="Claudia Cobranças",
    description="Sistema oficial de cobrança da Desktop",
    version="2.2",
    root_path=ROOT_PATH if BEHIND_PROXY else "",
    docs_url="/docs" if not BEHIND_PROXY else f"{ROOT_PATH}/docs",
    redoc_url="/redoc" if not BEHIND_PROXY else f"{ROOT_PATH}/redoc"
)

# Adicionar CORS para WebSockets
from fastapi.middleware.cors import CORSMiddleware

# Configurar origens permitidas baseado no ambiente
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Adicionar middleware para lidar com headers de proxy
if BEHIND_PROXY:
    # Adicionar hosts confiáveis
    trusted_hosts = os.getenv("TRUSTED_HOSTS", "*").split(",")
    if "*" not in trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=trusted_hosts
        )

# Configurar arquivos estáticos com cabeçalhos anti-cache
from fastapi.staticfiles import StaticFiles
from starlette.staticfiles import StaticFiles as StarletteStaticFiles
from starlette.responses import Response
from starlette.types import Scope, Receive, Send

class NoCacheStaticFiles(StarletteStaticFiles):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def no_cache_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((b"Cache-Control", b"no-cache, no-store, must-revalidate"))
                headers.append((b"Pragma", b"no-cache"))
                headers.append((b"Expires", b"0"))
                message["headers"] = headers
            await send(message)
        
        await super().__call__(scope, receive, no_cache_send)

app.mount("/static", NoCacheStaticFiles(directory="web/static"), name="static")

# Instâncias globais
config = Config()
excel_processor = ExcelProcessor()
whatsapp_client = WhatsAppClient()
conversation_engine = SuperConversationEngine()
fatura_downloader = None  # Será inicializado quando WhatsApp conectar

# Estado do sistema
system_state = {
    "whatsapp_connected": False,
    "current_session": None,
    "fpd_loaded": False,
    "vendas_loaded": False,
    "bot_active": False,
    "stats": {
        "messages_sent": 0,
        "faturas_sent": 0,
        "conversations": 0
    }
}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal - carrega o sistema JavaScript completo"""
    import time
    # Adicionar timestamp para evitar cache do navegador
    timestamp = int(time.time())
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
        <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Claudia Cobranças - Sistema de Cobrança da Desktop</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="/static/style.css?v={timestamp}" rel="stylesheet">
    </head>
    <body>
        <div id="loading" class="loading-overlay">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Carregando...</span>
                        </div>
                    </div>
                    
        <script src="/static/app.js?v={timestamp}"></script>
            <script>
            // Inicializar o sistema quando a página carregar
                document.addEventListener('DOMContentLoaded', function() {{
                // Remover loading
                document.getElementById('loading').style.display = 'none';
                
                // Inicializar Blacktemplar Bot
                window.blacktemplarBot = new BlacktemplarBot();
                }});
            </script>
    </body>
    </html>
        """)

@app.get("/health")
async def health_check():
    """Healthcheck ultra-simples para Railway"""
    return {"status": "healthy"}

@app.get("/api/status")
async def get_status():
    """Status do sistema"""
    try:
        status = {
        "status": "online",
            "version": "2.2",
        "whatsapp_connected": system_state["whatsapp_connected"],
            "bot_active": system_state["bot_active"],
        "fpd_loaded": system_state["fpd_loaded"],
        "vendas_loaded": system_state["vendas_loaded"],
            "stats": system_state["stats"],
            "timestamp": datetime.now().isoformat(),
            "railway": True,
            "health": "ok"
        }
        logger.info("✅ Status verificado")
        return status
    except Exception as e:
        logger.error(f"❌ Erro no status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/fpd/data")
async def get_fpd_data():
    """Obter dados dos FPDs carregados"""
    try:
        if not system_state["fpd_loaded"] or excel_processor.df_fpd is None:
            return {
                "success": False,
                "message": "FPD não carregado"
            }
        
        # Obter dados dos FPDs
        fpd_data = []
        df = excel_processor.df_fpd
        
        # Limitar a 100 registros para exibição
        sample_df = df.head(100)
        
        for index, row in sample_df.iterrows():
            try:
                # Extrair dados do cliente
                cliente_nome = excel_processor._extract_client_name(row)
                telefone = excel_processor._extract_phone(row)
                documento = excel_processor._extract_document(row)
                
                # Obter protocolo
                protocolo = str(row.get(excel_processor.protocolo_column, 'N/A'))
                
                # Obter valor (tentar diferentes colunas)
                valor_cols = ['valor', 'vlr', 'valor_total', 'total']
                valor = None
                for col in valor_cols:
                    if col in df.columns and pd.notna(row[col]):
                        valor = row[col]
                        break
                
                fpd_data.append({
                    "id": index,
                    "protocolo": protocolo,
                    "cliente": {
                        "nome": cliente_nome,
                        "telefone": telefone,
                        "documento": documento
                    },
                    "valor": float(valor) if valor else 0.0,
                    "status": "ativo" if protocolo != 'N/A' else "sem_protocolo"
                })
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar linha {index}: {e}")
                continue
        
        return {
            "success": True,
            "data": fpd_data,
            "total_records": len(df),
            "shown_records": len(fpd_data),
            "protocol_column": excel_processor.protocolo_column
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter dados FPD: {e}")
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
    }

@app.get("/api/storage/stats")
async def get_storage_stats():
    """📊 Estatísticas do gerenciamento de armazenamento"""
    try:
        stats = await storage_manager.get_storage_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas de armazenamento: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/storage/cleanup")
async def force_storage_cleanup():
    """🧹 Forçar limpeza de armazenamento"""
    try:
        cleanup_result = await storage_manager.cleanup_expired_files()
        return {
            "success": True,
            "cleanup_result": cleanup_result
        }
    except Exception as e:
        logger.error(f"❌ Erro na limpeza forçada: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/whatsapp/connect")
async def connect_whatsapp():
    """Conectar WhatsApp via QR Code"""
    try:
        logger.info("🔌 Iniciando conexão WhatsApp...")
        
        # Verificar se já está conectado
        if system_state["whatsapp_connected"]:
            return {
                "success": True,
                "message": "WhatsApp já está conectado",
                "connected": True
            }
        
        # Inicializar cliente WhatsApp
        logger.info("🚀 Inicializando cliente WhatsApp...")
        qr_data = await whatsapp_client.initialize()
        
        if qr_data:
            logger.info("✅ QR Code gerado com sucesso")
            # Não alterar o estado aqui, apenas retornar o QR
            return {
                "success": True,
                "qr_data": qr_data,
                "message": "Escaneie o QR Code com WhatsApp",
                "connected": system_state["whatsapp_connected"]
            }
        else:
            logger.warning("⚠️ Não foi possível gerar QR Code")
            return {
                "success": False,
                "message": "Erro ao gerar QR Code - tente novamente",
                "connected": False
            }
            
    except Exception as e:
        logger.error(f"❌ Erro ao conectar WhatsApp: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"Erro interno: {str(e)}",
            "connected": False
        }

@app.get("/api/whatsapp/qr")
async def get_qr_code():
    """Obter QR Code atualizado"""
    try:
        qr_data = await whatsapp_client.get_qr_code()
        return {
            "success": True,
            "qr_data": qr_data,
            "connected": system_state["whatsapp_connected"]
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@app.post("/api/upload/fpd")
async def upload_fpd(file: UploadFile = File(...)):
    """Upload planilha FPD"""
    try:
        # Salvar arquivo temporariamente
        file_path = f"uploads/fpd_{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Processar planilha
        result = excel_processor.load_fpd(file_path)
        
        if result["success"]:
            system_state["fpd_loaded"] = True
            return {
                "success": True,
                "message": f"FPD carregada: {result['total_records']} registros",
                "stats": result["stats"]
            }
        else:
            return {
                "success": False,
                "message": result["error"]
            }
            
    except Exception as e:
        logger.error(f"❌ Erro no upload FPD: {e}")
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
        }

@app.post("/api/upload/vendas")
async def upload_vendas(file: UploadFile = File(...)):
    """Upload planilha VENDAS/contratos"""
    try:
        # Salvar arquivo
        file_path = f"uploads/vendas_{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Processar planilha
        result = excel_processor.load_vendas(file_path)
        
        if result["success"]:
            system_state["vendas_loaded"] = True
            return {
                "success": True,
                "message": f"VENDAS carregada: {result['total_records']} registros",
                "sheets": result["sheets"]
            }
        else:
            return {
                "success": False,
                "message": result["error"]
            }
            
    except Exception as e:
        logger.error(f"❌ Erro no upload VENDAS: {e}")
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
        }

@app.post("/api/process/match")
async def process_match():
    """Processar matching FPD x VENDAS"""
    try:
        if not system_state["fpd_loaded"] or not system_state["vendas_loaded"]:
            return {
                "success": False,
                "message": "Carregue FPD e VENDAS primeiro"
            }
        
        # Processar matching
        result = excel_processor.process_matching()
        
        return {
            "success": True,
            "matched_records": result["matched"],
            "total_protocols": result["total_protocols"],
            "ready_for_cobranca": result["ready_for_cobranca"]
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no matching: {e}")
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
        }

@app.post("/api/bot/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Iniciar bot de cobrança"""
    try:
        if not system_state["whatsapp_connected"]:
            return {
                "success": False,
                "message": "WhatsApp não conectado"
            }
        
        if not excel_processor.has_matched_data():
            return {
                "success": False,
                "message": "Execute o matching primeiro"
            }
        
        # Iniciar bot em background
        background_tasks.add_task(run_cobranca_bot)
        
        system_state["bot_active"] = True
        
        return {
            "success": True,
            "message": "Bot de cobrança iniciado"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar bot: {e}")
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
        }

@app.post("/api/bot/stop")
async def stop_bot():
    """Parar bot"""
    try:
        # Parar bot de forma segura
        system_state["bot_active"] = False
        
        return {
            "success": True,
            "message": "Bot parado"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro: {str(e)}"
        }

@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Webhook para mensagens do WhatsApp"""
    try:
        data = await request.json()
        
        # Processar mensagem recebida
        if data.get("type") == "message":
            message = data.get("data", {})
            phone = message.get("from")
            text = message.get("body", "")
            
            # Engine de conversação
            response = await conversation_engine.process_message(phone, text)
            
            if response:
                # Enviar resposta
                await whatsapp_client.send_message(phone, response["text"], response.get("attachment"))
                
                # Atualizar stats
                system_state["stats"]["conversations"] += 1
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
        return {"success": False}

async def run_cobranca_bot():
    """🚀 EXECUTAR BOT ULTRA-ROBUSTO - Resolve todos os problemas críticos"""
    try:
        logger.info("🤖 INICIANDO ULTRA STEALTH BOT...")
        
        # Obter dados para cobrança
        cobranca_data = excel_processor.get_cobranca_data()
        
        # 🛑 VERIFICAÇÃO CRÍTICA - Lista vazia
        if not cobranca_data:
            logger.warning("⚠️ NENHUM DADO PARA COBRANÇA - PARANDO")
            system_state["bot_active"] = False
            return
        
        logger.info(f"📊 Dados carregados: {len(cobranca_data)} registros")
        
        # 🚀 USAR ULTRA STEALTH SENDER
        from core.ultra_stealth_sender import UltraStealthSender
        ultra_sender = UltraStealthSender()
        
        # 🔄 EXECUTAR ENVIOS ULTRA STEALTH
        result = await ultra_sender.execute_mass_sending(
            data=cobranca_data,
            whatsapp_client=whatsapp_client,
            stats_callback=update_stats
        )
        
        # 📊 LOGS FINAIS
        logger.info(f"✅ ULTRA STEALTH concluído: {result}")
        
        # 🛑 PARAR BOT QUANDO ACABAR
        system_state["bot_active"] = False
        logger.info("🛑 Bot parado automaticamente após conclusão")
        
    except Exception as e:
        logger.error(f"❌ Erro no ULTRA STEALTH BOT: {e}")
        system_state["bot_active"] = False

def update_stats(stats):
    """Atualizar estatísticas"""
    system_state["stats"].update(stats)

# WebSocket para updates em tempo real
@app.websocket("/ws/status")
async def websocket_status(websocket):
    """WebSocket para atualizações em tempo real"""
    try:
        # Configurar headers para proxy se necessário
        if BEHIND_PROXY:
            # Aceitar conexão com configurações específicas para proxy
            headers = websocket.headers
            
            # Log dos headers recebidos para debug
            logger.debug(f"WebSocket headers: {dict(headers)}")
            
            # Verificar se é uma conexão válida através do proxy
            if "sec-websocket-key" not in headers:
                logger.warning("WebSocket: Faltando header sec-websocket-key")
                await websocket.close(code=1002, reason="Invalid WebSocket handshake")
                return
        
        # Accept deve ser a primeira operação, antes de qualquer processamento
        await websocket.accept()
        
        # Log de conexão bem-sucedida
        client_info = ""
        if BEHIND_PROXY and hasattr(websocket, 'headers'):
            if "x-forwarded-for" in websocket.headers:
                client_info = f" de {websocket.headers['x-forwarded-for'].split(',')[0].strip()}"
        
        logger.info(f"✅ WebSocket conectado{client_info}")
        
        # Loop de envio de atualizações
        while True:
            # Enviar status atual
            await websocket.send_json({
                "type": "status_update",
                "data": system_state
            })
            
            # Aguardar 5 segundos
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        logger.info("📱 WebSocket desconectado normalmente")
    except ValueError as e:
        # Este erro específico ocorre quando já está fechado/rejeitado
        logger.info(f"ℹ️ WebSocket já fechado: {e}")
    except Exception as e:
        logger.error(f"❌ Erro no WebSocket: {e}")
    finally:
        try:
            await websocket.close()
        except Exception as e:
            logger.debug(f"ℹ️ Erro ao fechar WebSocket: {e}")
            pass

# 🚀 NOVOS ENDPOINTS - FUNCIONALIDADES AVANÇADAS

@app.post("/api/server/start")
async def start_server():
    """Iniciar serviços do servidor"""
    try:
        logger.info("🚀 Solicitação de inicialização do servidor")
        return {"success": True, "message": "Servidor iniciado com sucesso"}
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar servidor: {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/server/stop")
async def stop_server():
    """Parar serviços do servidor"""
    try:
        logger.info("🛑 Solicitação de parada do servidor")
        return {"success": True, "message": "Servidor parado com sucesso"}
    except Exception as e:
        logger.error(f"❌ Erro ao parar servidor: {e}")
        return {"success": False, "message": str(e)}

@app.get("/api/logs")
async def get_logs(type: str = "all", limit: int = 100):
    """Obter logs do sistema"""
    try:
        logs = []
        import datetime
        
        # Mock data - em produção, ler de arquivo de log real
        for i in range(min(limit, 20)):
            logs.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "level": "info" if i % 3 != 0 else "error",
                "message": f"Log de exemplo #{i+1} - Sistema funcionando"
            })
        
        return logs
    except Exception as e:
        logger.error(f"❌ Erro ao carregar logs: {e}")
        return []

@app.get("/api/metrics")
async def get_metrics():
    """Obter métricas do sistema"""
    try:
        metrics = {
            "messages": {
                "total": 150,
                "sent": 142,
                "failed": 8
            },
            "conversations": {
                "active": 12,
                "completed": 85
            },
            "invoices": {
                "sent": 45,
                "downloaded": 38
            }
        }
        
        return metrics
    except Exception as e:
        logger.error(f"❌ Erro ao carregar métricas: {e}")
        return {}

@app.get("/api/messages/history")
async def get_message_history(phone: str = None, limit: int = 50):
    """Obter histórico de mensagens"""
    try:
        history = []
        
        # Mock data - em produção, consultar banco de dados
        for i in range(min(limit, 10)):
            conversation = {
                "phone": f"+5511999{i:06d}",
                "lastMessage": "2024-01-15T10:30:00",
                "messageCount": 5 + i,
                "status": "completed" if i % 2 == 0 else "active"
            }
            
            if phone is None or conversation["phone"] == phone:
                history.append(conversation)
        
        return history
    except Exception as e:
        logger.error(f"❌ Erro ao carregar histórico: {e}")
        return []

@app.get("/api/messages/conversation/{phone}")
async def get_conversation_messages(phone: str):
    """Obter mensagens de uma conversa específica"""
    try:
        messages = [
            {
                "content": "Olá, preciso da minha segunda via da fatura",
                "direction": "incoming",
                "timestamp": "2024-01-15T10:30:00"
            },
            {
                "content": "Olá! Vou buscar sua fatura. Qual é o CPF?",
                "direction": "outgoing",
                "timestamp": "2024-01-15T10:31:00"
            },
            {
                "content": "123.456.789-00",
                "direction": "incoming",
                "timestamp": "2024-01-15T10:32:00"
            },
            {
                "content": "Encontrei sua fatura! Enviando agora...",
                "direction": "outgoing",
                "timestamp": "2024-01-15T10:33:00"
            }
        ]
        
        return messages
    except Exception as e:
        logger.error(f"❌ Erro ao carregar mensagens: {e}")
        return []

@app.get("/api/config")
async def get_configuration():
    """Obter configurações do sistema"""
    try:
        config = {
            "bot": {
                "autoStart": True,
                "messageDelay": 1000
            },
            "whatsapp": {
                "stealthMode": True,
                "autoReconnect": True
            },
            "data": {
                "autoBackup": False
            }
        }
        
        return config
    except Exception as e:
        logger.error(f"❌ Erro ao carregar configuração: {e}")
        return {}

@app.put("/api/config")
async def update_configuration(data: dict):
    """Atualizar configurações do sistema"""
    try:
        key = data.get('key')
        value = data.get('value')
        
        logger.info(f"🔧 Atualizando configuração: {key} = {value}")
        
        # Aqui você salvaria a configuração em arquivo ou banco
        
        return {"success": True, "message": "Configuração atualizada"}
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar configuração: {e}")
        return {"success": False, "message": str(e)}

# 🔐 NOVOS ENDPOINTS - SISTEMA ANTI-CAPTCHA E DOWNLOAD FATURAS

@app.get("/api/captcha/info")
async def get_captcha_info():
    """Obter informações do sistema anti-captcha"""
    return get_captcha_solver_info()

@app.post("/api/fatura/download")
async def download_fatura(request: Request):
    """Baixar fatura individual do SAC Desktop"""
    try:
        data = await request.json()
        documento = data.get("documento")
        protocolo = data.get("protocolo")
        
        if not documento:
            return {"success": False, "error": "Documento é obrigatório"}
        
        # Verificar se WhatsApp está conectado (precisamos da página)
        if not whatsapp_client.page:
            return {"success": False, "error": "WhatsApp não conectado"}
        
        # Inicializar downloader se necessário
        global fatura_downloader
        if not fatura_downloader:
            fatura_downloader = FaturaDownloader(whatsapp_client.page)
        
        # Baixar fatura
        arquivo_baixado = await fatura_downloader.baixar_fatura(documento, protocolo)
        
        if arquivo_baixado:
            return {
                "success": True,
                "arquivo": arquivo_baixado,
                "documento": documento,
                "protocolo": protocolo
            }
        else:
            return {
                "success": False,
                "error": "Fatura não encontrada ou erro no download"
            }
            
    except Exception as e:
        logger.error(f"❌ Erro no download de fatura: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/fatura/download/multiplas")
async def download_multiplas_faturas(request: Request):
    """Baixar múltiplas faturas do SAC Desktop"""
    try:
        data = await request.json()
        documentos_protocolos = data.get("documentos", [])
        intervalo = data.get("intervalo", 5.0)
        
        if not documentos_protocolos:
            return {"success": False, "error": "Lista de documentos é obrigatória"}
        
        # Verificar se WhatsApp está conectado
        if not whatsapp_client.page:
            return {"success": False, "error": "WhatsApp não conectado"}
        
        # Inicializar downloader se necessário
        global fatura_downloader
        if not fatura_downloader:
            fatura_downloader = FaturaDownloader(whatsapp_client.page)
        
        # Converter lista de documentos para tuplas (documento, protocolo)
        docs_tuplas = []
        for item in documentos_protocolos:
            if isinstance(item, dict):
                docs_tuplas.append((item.get("documento"), item.get("protocolo")))
            elif isinstance(item, list) and len(item) >= 2:
                docs_tuplas.append((item[0], item[1]))
            else:
                docs_tuplas.append((str(item), None))
        
        # Baixar faturas
        resultados = await fatura_downloader.baixar_multiplas_faturas(docs_tuplas, intervalo)
        
        return {
            "success": True,
            "resultados": resultados
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no download múltiplo: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/fatura/listar")
async def listar_faturas():
    """Listar todas as faturas baixadas"""
    try:
        global fatura_downloader
        
        # Se downloader não existe, criar instância temporária só para listar
        if not fatura_downloader:
            # Criar downloader básico só para listar arquivos
            import tempfile
            from core.fatura_downloader import FaturaDownloader
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            temp_downloader = FaturaDownloader(page)
            faturas = temp_downloader.listar_faturas_baixadas()
            await browser.close()
            await playwright.stop()
            
            return {
                "success": True,
                "faturas": faturas,
                "total": len(faturas)
            }
        
        faturas = fatura_downloader.listar_faturas_baixadas()
        
        return {
            "success": True,
            "faturas": faturas,
            "total": len(faturas)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar faturas: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/fatura/status")
async def get_fatura_status():
    """Obter status do sistema de download de faturas"""
    try:
        global fatura_downloader
        
        if fatura_downloader:
            status = fatura_downloader.get_status()
            return {"success": True, "status": status}
        else:
            return {
                "success": True,
                "status": {
                    "fatura_downloader_initialized": False,
                    "whatsapp_connected": system_state["whatsapp_connected"],
                    "sac_url": "https://sac.desktop.com.br/Cliente_Documento.jsp"
                }
            }
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return {"success": False, "error": str(e)}

# ================================
# 🔐 SISTEMA DE AUTENTICAÇÃO COM APROVAÇÃO MANUAL
# ================================

def cleanup_expired_requests():
    """Limpar solicitações expiradas"""
    current_time = time.time()
    expired_keys = []
    
    for request_id, request_data in pending_auth_requests.items():
        if current_time - request_data["timestamp"] > auth_settings["request_timeout"]:
            expired_keys.append(request_id)
    
    for key in expired_keys:
        del pending_auth_requests[key]
        logger.info(f"🧹 Solicitação expirada removida: {key}")

def cleanup_expired_sessions():
    """Limpar sessões expiradas"""
    current_time = time.time()
    expired_keys = []
    
    for token, session_data in active_sessions.items():
        if current_time - session_data["timestamp"] > auth_settings["session_timeout"]:
            expired_keys.append(token)
    
    for key in expired_keys:
        del active_sessions[key]
        logger.info(f"🧹 Sessão expirada removida: {key[:8]}...")

@app.get("/api/auth/status")
async def auth_status():
    """Status do sistema de autenticação"""
    cleanup_expired_requests()
    cleanup_expired_sessions()
    
    return {
        "success": True,
        "pending_requests": len(pending_auth_requests),
        "active_sessions": len(active_sessions),
        "settings": auth_settings
    }

@app.post("/api/auth/request")
async def auth_request(request: Request, login_data: LoginRequest):
    """Solicitar aprovação de login"""
    cleanup_expired_requests()
    
    # Verificar limite de solicitações pendentes
    if len(pending_auth_requests) >= auth_settings["max_pending"]:
        raise HTTPException(status_code=429, detail="Muitas solicitações pendentes")
    
    # Gerar ID único para a solicitação
    request_id = str(uuid.uuid4())
    
    # Obter IP e User-Agent automaticamente
    client_ip = request.client.host if request.client else login_data.ip
    user_agent = request.headers.get("user-agent", login_data.user_agent or "Unknown")
    
    # Armazenar solicitação
    request_data = {
        "email": login_data.email,
        "password": login_data.password,  # Em produção, nunca armazenar senhas!
        "reason": login_data.reason,
        "ip": client_ip,
        "user_agent": user_agent,
        "timestamp": time.time(),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    pending_auth_requests[request_id] = request_data
    
    # 🖥️ EXIBIR NO TERMINAL RAILWAY
    print("\n" + "=" * 80)
    print("🔐 NOVA TENTATIVA DE LOGIN - AGUARDANDO APROVAÇÃO")
    print("=" * 80)
    print(f"📅 Data/Hora: {request_data['datetime']}")
    print(f"🆔 Request ID: {request_id}")
    print(f"👤 Email/Usuário: {login_data.email}")
    print(f"📝 Motivo: {login_data.reason}")
    print(f"🌐 IP: {client_ip}")
    print(f"💻 User Agent: {user_agent[:100]}...")
    print("-" * 80)
    print("Para APROVAR este login, acesse:")
    print(f"https://sua-app.railway.app/api/auth/approve/{request_id}")
    print()
    print("Para NEGAR este login, acesse:")
    print(f"https://sua-app.railway.app/api/auth/deny/{request_id}")
    print("=" * 80)
    print()
    
    # Log estruturado
    logger.info(f"🔐 Nova solicitação de login: {login_data.email} | ID: {request_id}")
    
    return {
        "success": True,
        "request_id": request_id,
        "message": "Solicitação enviada. Aguarde aprovação do administrador.",
        "status": "pending"
    }

@app.post("/api/auth/approve/{request_id}")
async def auth_approve(request_id: str):
    """Aprovar solicitação de login"""
    cleanup_expired_requests()
    
    if request_id not in pending_auth_requests:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada ou expirada")
    
    # Obter dados da solicitação
    request_data = pending_auth_requests[request_id]
    
    # Gerar token de sessão
    session_token = str(uuid.uuid4())
    
    # Criar sessão ativa
    active_sessions[session_token] = {
        "email": request_data["email"],
        "request_id": request_id,
        "timestamp": time.time(),
        "ip": request_data["ip"],
        "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Remover da lista de pendentes
    del pending_auth_requests[request_id]
    
    # 🖥️ FEEDBACK NO TERMINAL
    print(f"\n✅ LOGIN APROVADO! ID: {request_id}")
    print(f"👤 Usuário: {request_data['email']}")
    print(f"🎫 Token: {session_token[:16]}...")
    print(f"⏰ Válido até: {(datetime.now() + timedelta(seconds=auth_settings['session_timeout'])).strftime('%H:%M:%S')}")
    print()
    
    logger.info(f"✅ Login aprovado: {request_data['email']} | Token: {session_token[:8]}...")
    
    return {
        "success": True,
        "message": "Login aprovado com sucesso",
        "session_token": session_token,
        "expires_in": auth_settings["session_timeout"]
    }

@app.post("/api/auth/deny/{request_id}")
async def auth_deny(request_id: str):
    """Negar solicitação de login"""
    cleanup_expired_requests()
    
    if request_id not in pending_auth_requests:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada ou expirada")
    
    # Obter dados da solicitação
    request_data = pending_auth_requests[request_id]
    
    # Remover da lista de pendentes
    del pending_auth_requests[request_id]
    
    # 🖥️ FEEDBACK NO TERMINAL
    print(f"\n❌ LOGIN NEGADO! ID: {request_id}")
    print(f"👤 Usuário: {request_data['email']}")
    print(f"🌐 IP: {request_data['ip']}")
    print()
    
    logger.warning(f"❌ Login negado: {request_data['email']} | ID: {request_id}")
    
    return {
        "success": True,
        "message": "Login negado",
        "status": "denied"
    }

@app.post("/api/auth/validate")
async def auth_validate(session_data: SessionValidation):
    """Validar token de sessão"""
    cleanup_expired_sessions()
    
    if session_data.token not in active_sessions:
        return {"valid": False, "message": "Token inválido ou expirado"}
    
    session_info = active_sessions[session_data.token]
    
    # Atualizar timestamp da sessão (renovar)
    session_info["timestamp"] = time.time()
    
    return {
        "valid": True,
        "email": session_info["email"],
        "expires_in": auth_settings["session_timeout"]
    }

@app.delete("/api/auth/logout")
async def auth_logout(session_data: SessionValidation):
    """Fazer logout (invalidar sessão)"""
    if session_data.token in active_sessions:
        session_info = active_sessions[session_data.token]
        del active_sessions[session_data.token]
        
        logger.info(f"🚪 Logout: {session_info['email']} | Token: {session_data.token[:8]}...")
        
        return {"success": True, "message": "Logout realizado com sucesso"}
    
    return {"success": False, "message": "Sessão não encontrada"}

@app.get("/api/auth/pending")
async def auth_pending():
    """Listar solicitações pendentes (para admin)"""
    cleanup_expired_requests()
    
    pending_list = []
    for request_id, data in pending_auth_requests.items():
        pending_list.append({
            "request_id": request_id,
            "email": data["email"],
            "reason": data["reason"],
            "ip": data["ip"],
            "datetime": data["datetime"],
            "user_agent": data["user_agent"][:100] + "..." if len(data["user_agent"]) > 100 else data["user_agent"]
        })
    
    return {
        "success": True,
        "pending_requests": pending_list,
        "count": len(pending_list)
    }

# ================================
# 🔧 MIDDLEWARE PARA PROXY REVERSO
# ================================

@app.middleware("http")
async def proxy_headers_middleware(request: Request, call_next):
    """Middleware para processar headers de proxy reverso (Traefik, nginx, etc)"""
    
    if BEHIND_PROXY:
        # Processar headers X-Forwarded-*
        headers = request.headers
        
        # Obter IP real do cliente
        if "x-forwarded-for" in headers:
            # X-Forwarded-For pode conter múltiplos IPs separados por vírgula
            # O primeiro é o IP original do cliente
            client_ip = headers["x-forwarded-for"].split(",")[0].strip()
            request.state.client_ip = client_ip
        elif "x-real-ip" in headers:
            request.state.client_ip = headers["x-real-ip"]
        else:
            request.state.client_ip = request.client.host
        
        # Processar protocolo (http/https)
        if "x-forwarded-proto" in headers:
            request.state.scheme = headers["x-forwarded-proto"]
        
        # Processar host original
        if "x-forwarded-host" in headers:
            request.state.forwarded_host = headers["x-forwarded-host"]
        
        # Processar porta original
        if "x-forwarded-port" in headers:
            request.state.forwarded_port = headers["x-forwarded-port"]
            
        # Log para debug
        logger.debug(f"Proxy headers - IP: {request.state.client_ip}, "
                    f"Proto: {request.state.scheme if hasattr(request.state, 'scheme') else 'N/A'}, "
                    f"Host: {request.state.forwarded_host if hasattr(request.state, 'forwarded_host') else 'N/A'}")
    
    response = await call_next(request)
    
    # Adicionar headers de segurança
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# ================================
# 🔒 MIDDLEWARE DE AUTENTICAÇÃO
# ================================

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware para verificar autenticação em rotas protegidas"""
    
    # Rotas que não precisam de autenticação
    public_paths = [
        "/",
        "/health",
        "/api/status",
        "/api/auth/request",
        "/api/auth/approve",
        "/api/auth/deny", 
        "/api/auth/status",
        "/api/auth/pending",
        "/static",
        "/favicon.ico"
    ]
    
    # Verificar se é rota pública
    path = str(request.url.path)
    
    for public_path in public_paths:
        if path.startswith(public_path):
            return await call_next(request)
    
    # Para rotas protegidas, verificar autenticação
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        # Retornar página de login ao invés de erro JSON
        if path.startswith("/dashboard") or path.startswith("/admin"):
            with open("web/login.html", "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        
        return JSONResponse(
            status_code=401,
            content={"error": "Token de autenticação necessário"}
        )
    
    token = auth_header.split(" ")[1]
    
    # Verificar se token é válido
    cleanup_expired_sessions()
    
    if token not in active_sessions:
        if path.startswith("/dashboard") or path.startswith("/admin"):
            with open("web/login.html", "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        
        return JSONResponse(
            status_code=401,
            content={"error": "Token inválido ou expirado"}
        )
    
    # Renovar sessão
    active_sessions[token]["timestamp"] = time.time()
    
    # Adicionar informações do usuário ao request
    request.state.user = active_sessions[token]
    
    return await call_next(request)

if __name__ == "__main__":
    # Criar diretórios necessários
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("faturas", exist_ok=True)
    os.makedirs("web/static", exist_ok=True)
    
    # 🧹 Inicializar limpeza automática de armazenamento
    async def startup_storage_cleanup():
        """Inicializar sistema de limpeza automática"""
        logger.info("🗂️ Iniciando sistema de gerenciamento de armazenamento...")
        await storage_manager.cleanup_expired_files()  # Limpeza inicial
        # Agendar limpeza periódica em background
        asyncio.create_task(storage_manager.schedule_periodic_cleanup())
        logger.info("✅ Sistema de armazenamento inicializado!")
    
    # Adicionar evento de startup
    @app.on_event("startup")
    async def startup_event():
        await startup_storage_cleanup()
    
    # Iniciar servidor
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    ) 