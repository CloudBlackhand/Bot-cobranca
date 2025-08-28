#!/usr/bin/env python3
"""
Script Simples para Configurar WhatsApp no Railway
"""

import requests
import qrcode
import time
import sys

def setup_whatsapp():
    print("🤖 CONFIGURAÇÃO DO WHATSAPP NO RAILWAY")
    print("="*50)
    
    # Pede a URL do WAHA
    waha_url = input("\n📋 Cole a URL do seu WAHA (ex: https://waha-production-abc123.up.railway.app): ").strip()
    
    if not waha_url.startswith("http"):
        waha_url = "https://" + waha_url
    
    print(f"\n🔄 Conectando em: {waha_url}")
    
    # Testa conexão
    try:
        response = requests.get(f"{waha_url}/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ WAHA está funcionando!")
        else:
            print(f"❌ Erro: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Não consegui conectar: {e}")
        print("\n💡 Dicas:")
        print("- Verifique se a URL está correta")
        print("- Aguarde o deploy terminar no Railway")
        print("- Tente novamente em 1 minuto")
        return
    
    # Cria sessão
    print("\n📱 Criando sessão WhatsApp...")
    try:
        session_data = {
            "name": "claudia-cobrancas",
            "config": {
                "webhook": {
                    "url": "",
                    "events": ["message"]
                }
            }
        }
        
        response = requests.post(
            f"{waha_url}/api/sessions",
            json=session_data,
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            print("✅ Sessão criada!")
        elif response.status_code == 409:
            print("ℹ️ Sessão já existe, continuando...")
        else:
            print(f"⚠️ Resposta: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Erro ao criar sessão: {e}")
    
    # Pega QR Code
    print("\n📲 Obtendo QR Code...")
    max_tentativas = 10
    
    for tentativa in range(max_tentativas):
        try:
            response = requests.get(
                f"{waha_url}/api/sessions/claudia-cobrancas/auth/qr",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                qr_data = data.get('qr', '')
                
                if qr_data:
                    print("\n✅ QR CODE GERADO!")
                    print("="*50)
                    
                    # Gera QR Code
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    
                    # Mostra no terminal
                    qr.print_ascii(invert=True)
                    
                    # Salva como imagem
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save('whatsapp_qr.png')
                    
                    print("\n📱 INSTRUÇÕES:")
                    print("1. Abra o WhatsApp no seu celular")
                    print("2. Vá em Configurações > Dispositivos conectados")
                    print("3. Toque em 'Conectar dispositivo'")
                    print("4. Escaneie o QR Code acima")
                    print("\n💾 QR Code também salvo em: whatsapp_qr.png")
                    
                    # Aguarda conexão
                    print("\n⏳ Aguardando conexão...")
                    for i in range(60):
                        time.sleep(2)
                        try:
                            status_response = requests.get(
                                f"{waha_url}/api/sessions/claudia-cobrancas",
                                timeout=5
                            )
                            if status_response.status_code == 200:
                                status = status_response.json().get('status', '')
                                if status == 'WORKING':
                                    print("\n🎉 WHATSAPP CONECTADO COM SUCESSO!")
                                    print("✅ Tudo pronto! Claudia pode enviar mensagens!")
                                    return
                                elif status != 'SCAN_QR_CODE':
                                    print(f"\nStatus: {status}")
                        except:
                            pass
                        
                        if i % 5 == 0:
                            print(f"⏳ Aguardando... ({60-i*2}s)")
                    
                    print("\n⏰ Tempo esgotado. Execute novamente se não conectou.")
                    return
                    
                else:
                    print(f"⏳ Aguardando QR... tentativa {tentativa+1}/{max_tentativas}")
                    time.sleep(3)
            else:
                print(f"⏳ Preparando... tentativa {tentativa+1}/{max_tentativas}")
                time.sleep(3)
                
        except Exception as e:
            print(f"⏳ Conectando... tentativa {tentativa+1}/{max_tentativas}")
            time.sleep(3)
    
    print("\n❌ Não foi possível obter o QR Code.")
    print("💡 Tente novamente em alguns minutos.")

if __name__ == "__main__":
    setup_whatsapp()