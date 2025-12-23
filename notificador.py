"""
Módulo de Notificações - Telegram

Envia notificações sobre variações de preço via Telegram Bot.

CONFIGURAÇÃO:
1. Crie um bot no Telegram conversando com @BotFather
2. Crie o arquivo 'config_telegram.json' com:
   {
     "bot_token": "SEU_TOKEN_AQUI",
     "chat_id": "SEU_CHAT_ID_AQUI"
   }
3. Para descobrir seu chat_id, envie uma mensagem para o bot e acesse:
   https://api.telegram.org/bot<TOKEN>/getUpdates

Uso:
    from notificador import enviar_notificacao
    enviar_notificacao("Preço do produto X desceu!")
"""

import json
import os
import requests
from typing import Optional

CONFIG_FILE = "config_telegram.json"


def carregar_config() -> Optional[dict]:
    """Carrega as configurações do Telegram do arquivo JSON."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def enviar_notificacao(mensagem: str) -> bool:
    """
    Envia uma notificação via Telegram.
    
    Args:
        mensagem: Texto da mensagem a ser enviada.
    
    Returns:
        True se enviou com sucesso, False caso contrário.
    """
    config = carregar_config()
    
    if not config:
        print(f"[Notificador] Arquivo {CONFIG_FILE} não encontrado. Notificações desativadas.")
        return False
    
    bot_token = config.get('bot_token')
    chat_id = config.get('chat_id')
    
    if not bot_token or not chat_id:
        print("[Notificador] Configuração incompleta. Verifique bot_token e chat_id.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensagem,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        print("[Notificador] Mensagem enviada com sucesso!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[Notificador] Erro ao enviar mensagem: {e}")
        return False


def notificar_variacoes(produtos: list, limite_variacao: float = 5.0):
    """
    Envia notificação se houver variações significativas de preço.
    
    Args:
        produtos: Lista de produtos com variações.
        limite_variacao: Percentual mínimo para notificar (padrão: 5%).
    """
    produtos_notificar = []
    
    for p in produtos:
        variacao = p.get('variacao')
        if variacao is not None and abs(variacao) >= limite_variacao:
            produtos_notificar.append(p)
    
    if not produtos_notificar:
        print("[Notificador] Nenhuma variação significativa para notificar.")
        return
    
    # Monta a mensagem
    linhas = ["<b>🔔 Alerta de Variação de Preços</b>", ""]
    
    for p in produtos_notificar:
        var = p['variacao']
        emoji = "📈" if var > 0 else "📉"
        nome = p.get('nome') or p['ean']
        preco = p.get('preco_atual', 0)
        
        linhas.append(f"{emoji} <b>{nome[:40]}</b>")
        linhas.append(f"   Preço: R$ {preco:.2f} ({var:+.1f}%)")
        linhas.append("")
    
    mensagem = "\n".join(linhas)
    enviar_notificacao(mensagem)


# Exemplo de uso
if __name__ == "__main__":
    # Teste de envio
    print("Testando envio de notificação...")
    sucesso = enviar_notificacao("🧪 Teste de notificação do Monitor de Preços!")
    if sucesso:
        print("✅ Notificação enviada!")
    else:
        print("❌ Falha ao enviar. Verifique a configuração.")
