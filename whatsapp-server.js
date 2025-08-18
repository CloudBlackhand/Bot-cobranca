#!/usr/bin/env node
/**
 * WhatsApp Web.js Server - Claudia Cobranças
 * Servidor Node.js para gerenciar WhatsApp Web
 * Otimizado para Railway com Puppeteer args especiais
 */

const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

// Porta do servidor WhatsApp
const PORT = process.env.WHATSAPP_PORT || 3333;

// Estado global
let whatsappClient = null;
let qrCodeData = null;
let isConnected = false;
let connectionStatus = 'disconnected';

// Configuração otimizada do Puppeteer para Railway
const puppeteerArgs = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-accelerated-2d-canvas',
    '--no-first-run',
    '--no-zygote',
    '--single-process', // Importante para Railway
    '--disable-gpu',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
    '--disable-blink-features=AutomationControlled',
    '--disable-software-rasterizer',
    '--window-size=1920,1080'
];

// Configuração do cliente WhatsApp
function initializeWhatsApp() {
    console.log('🚀 Inicializando WhatsApp Web.js...');
    
    whatsappClient = new Client({
        authStrategy: new LocalAuth({
            clientId: 'claudia-cobrancas',
            dataPath: './whatsapp-sessions'
        }),
        puppeteer: {
            headless: true,
            args: puppeteerArgs,
            executablePath: process.env.CHROME_BIN || '/usr/bin/chromium-browser' || 'chromium'
        },
        webVersionCache: {
            type: 'remote',
            remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
        }
    });

    // Evento: QR Code gerado
    whatsappClient.on('qr', (qr) => {
        console.log('📱 QR Code gerado!');
        qrCodeData = qr;
        connectionStatus = 'waiting_qr';
        
        // Gerar QR code como imagem base64
        qrcode.toDataURL(qr, (err, url) => {
            if (!err) {
                qrCodeData = url;
            }
        });
    });

    // Evento: Cliente pronto
    whatsappClient.on('ready', () => {
        console.log('✅ WhatsApp conectado com sucesso!');
        isConnected = true;
        connectionStatus = 'connected';
        qrCodeData = null;
    });

    // Evento: Autenticado
    whatsappClient.on('authenticated', () => {
        console.log('🔐 WhatsApp autenticado!');
    });

    // Evento: Falha na autenticação
    whatsappClient.on('auth_failure', (msg) => {
        console.error('❌ Falha na autenticação:', msg);
        connectionStatus = 'auth_failed';
        isConnected = false;
    });

    // Evento: Desconectado
    whatsappClient.on('disconnected', (reason) => {
        console.log('🔌 WhatsApp desconectado:', reason);
        isConnected = false;
        connectionStatus = 'disconnected';
        
        // Tentar reconectar após 5 segundos
        setTimeout(() => {
            console.log('🔄 Tentando reconectar...');
            initializeWhatsApp();
        }, 5000);
    });

    // Evento: Mensagem recebida
    whatsappClient.on('message', async (message) => {
        console.log('📨 Mensagem recebida:', message.from, message.body);
        
        // Aqui você pode processar mensagens recebidas
        // e enviar para o Python via webhook se necessário
    });

    // Inicializar cliente
    whatsappClient.initialize().catch(err => {
        console.error('❌ Erro ao inicializar WhatsApp:', err);
        connectionStatus = 'error';
    });
}

// ====== ROTAS DA API ======

// Status da conexão
app.get('/status', (req, res) => {
    res.json({
        connected: isConnected,
        status: connectionStatus,
        hasQR: qrCodeData !== null
    });
});

// Obter QR Code
app.get('/qr', (req, res) => {
    if (qrCodeData) {
        res.json({
            success: true,
            qr: qrCodeData
        });
    } else {
        res.json({
            success: false,
            message: 'QR Code não disponível'
        });
    }
});

// Enviar mensagem
app.post('/send-message', async (req, res) => {
    const { number, message, mediaUrl } = req.body;
    
    if (!isConnected) {
        return res.status(400).json({
            success: false,
            message: 'WhatsApp não conectado'
        });
    }
    
    try {
        // Formatar número (adicionar @c.us se necessário)
        const chatId = number.includes('@') ? number : `${number}@c.us`;
        
        if (mediaUrl) {
            // Enviar mídia
            const media = await MessageMedia.fromUrl(mediaUrl);
            await whatsappClient.sendMessage(chatId, media, { caption: message });
        } else {
            // Enviar texto simples
            await whatsappClient.sendMessage(chatId, message);
        }
        
        res.json({
            success: true,
            message: 'Mensagem enviada com sucesso'
        });
    } catch (error) {
        console.error('❌ Erro ao enviar mensagem:', error);
        res.status(500).json({
            success: false,
            message: 'Erro ao enviar mensagem',
            error: error.message
        });
    }
});

// Verificar se número existe no WhatsApp
app.post('/check-number', async (req, res) => {
    const { number } = req.body;
    
    if (!isConnected) {
        return res.status(400).json({
            success: false,
            message: 'WhatsApp não conectado'
        });
    }
    
    try {
        const isRegistered = await whatsappClient.isRegisteredUser(`${number}@c.us`);
        res.json({
            success: true,
            exists: isRegistered
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Erro ao verificar número',
            error: error.message
        });
    }
});

// Desconectar WhatsApp
app.post('/disconnect', async (req, res) => {
    if (whatsappClient) {
        await whatsappClient.logout();
        isConnected = false;
        connectionStatus = 'disconnected';
        res.json({
            success: true,
            message: 'WhatsApp desconectado'
        });
    } else {
        res.json({
            success: false,
            message: 'WhatsApp não estava conectado'
        });
    }
});

// Reconectar WhatsApp
app.post('/reconnect', (req, res) => {
    initializeWhatsApp();
    res.json({
        success: true,
        message: 'Reconexão iniciada'
    });
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        whatsapp: connectionStatus,
        uptime: process.uptime()
    });
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 Servidor WhatsApp rodando na porta ${PORT}`);
    console.log(`📊 Status: http://localhost:${PORT}/status`);
    console.log(`🏥 Health: http://localhost:${PORT}/health`);
    
    // Inicializar WhatsApp automaticamente
    initializeWhatsApp();
});

// Tratamento de erros não capturados
process.on('uncaughtException', (err) => {
    console.error('❌ Erro não capturado:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Promise rejeitada:', reason);
});