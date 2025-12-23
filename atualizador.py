"""
Script de Atualização de Preços - Pague Menos (Ferramenta de Pricing)

Este script lê a lista de produtos em 'produtos.json', busca os preços
atualizados usando o scraper_core.py e atualiza o arquivo com os novos dados,
calculando a variação de preço e salvando histórico.

Uso: python atualizador.py
"""

import json
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

# Timezone de Brasília
BR_TZ = ZoneInfo("America/Sao_Paulo")

# Importa a função de scraping do módulo existente
from scraper_core import scrape_by_eans

# --- CONFIGURAÇÕES ---
PRODUTOS_FILE = "produtos.json"
MAX_HISTORICO = 30  # Máximo de pontos de histórico por produto


def log(message: str):
    """Função de log com timestamp no horário de Brasília."""
    timestamp = datetime.now(BR_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def carregar_produtos() -> list:
    """Carrega a lista de produtos do arquivo JSON."""
    if not os.path.exists(PRODUTOS_FILE):
        log(f"Arquivo {PRODUTOS_FILE} não encontrado.")
        return []
    try:
        with open(PRODUTOS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("produtos", [])
    except (json.JSONDecodeError, IOError) as e:
        log(f"Erro ao carregar {PRODUTOS_FILE}: {e}")
        return []


def salvar_produtos(produtos: list):
    """Salva a lista de produtos no arquivo JSON."""
    with open(PRODUTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"produtos": produtos}, f, ensure_ascii=False, indent=2)
    log(f"Arquivo {PRODUTOS_FILE} atualizado com sucesso.")


def extrair_preco_e_nome(resultado: dict) -> tuple[Optional[float], Optional[str]]:
    """
    Extrai o preço e o nome do produto a partir do dicionário retornado pelo scraper.
    
    A estrutura do retorno do scraper_core é:
    - items[0]['sellers'][0]['commertialOffer']['Price'] (ou 'price')
    - O nome está em 'name' ou 'productName'
    
    Retorna: (preco, nome) ou (None, None) se não encontrado.
    """
    try:
        # Verifica se é um produto não encontrado
        if resultado.get('is_not_found'):
            return None, None
        
        # Extrai o nome do produto
        nome = resultado.get('name') or resultado.get('productName', '')
        
        # Navega até a oferta comercial
        items = resultado.get('items', [])
        if not items:
            log(f"  -> Produto sem itens/SKUs.")
            return None, nome
        
        # Pega o primeiro item (SKU)
        primeiro_item = items[0]
        sellers = primeiro_item.get('sellers', [])
        
        if not sellers:
            log(f"  -> Produto sem sellers.")
            return None, nome
        
        # Pega a oferta do primeiro seller
        oferta = sellers[0].get('commertialOffer', {})
        
        if not oferta:
            log(f"  -> Produto sem oferta comercial.")
            return None, nome
        
        # Tenta extrair o preço (a chave pode ser 'Price' ou 'price')
        preco = oferta.get('price') or oferta.get('Price')
        
        if preco is None or preco == 0:
            # Tenta o preço de lista como fallback
            preco = oferta.get('listPrice') or oferta.get('ListPrice')
        
        if preco and preco > 0:
            return round(float(preco), 2), nome
        else:
            return None, nome
            
    except (IndexError, KeyError, TypeError) as e:
        log(f"  -> Erro ao extrair preço: {e}")
        return None, None


def calcular_variacao(preco_atual: float, preco_anterior: float) -> float:
    """Calcula a variação percentual entre dois preços."""
    if preco_anterior is None or preco_anterior == 0:
        return 0.0
    return round(((preco_atual - preco_anterior) / preco_anterior) * 100, 2)


def adicionar_ao_historico(produto: dict, preco: float):
    """Adiciona um ponto de preço ao histórico do produto."""
    if 'historico' not in produto:
        produto['historico'] = []
    
    novo_ponto = {
        "data": datetime.now(BR_TZ).isoformat(),
        "preco": preco
    }
    
    produto['historico'].append(novo_ponto)
    
    # Limita o tamanho do histórico
    if len(produto['historico']) > MAX_HISTORICO:
        produto['historico'] = produto['historico'][-MAX_HISTORICO:]


def atualizar_produtos():
    """Função principal que atualiza os preços dos produtos."""
    log("=" * 60)
    log("Iniciando atualização de preços (Ferramenta de Pricing)...")
    log("=" * 60)
    
    # Carrega os produtos
    produtos = carregar_produtos()
    
    if not produtos:
        log("Nenhum produto encontrado para atualizar.")
        return
    
    log(f"Total de {len(produtos)} produtos cadastrados.")
    
    # Extrai a lista de EANs
    eans = [p['ean'] for p in produtos]
    log(f"EANs para buscar: {eans}")
    
    # Chama o scraper para buscar os dados
    log("-" * 60)
    log("Iniciando busca via scraper_core.scrape_by_eans...")
    log("-" * 60)
    
    try:
        resultados = scrape_by_eans(eans, log_callback=log)
    except Exception as e:
        log(f"ERRO CRÍTICO ao chamar o scraper: {e}")
        for produto in produtos:
            produto['status'] = 'Erro'
            produto['ultima_verificacao'] = datetime.now(BR_TZ).isoformat()
        salvar_produtos(produtos)
        return
    
    log("-" * 60)
    log(f"Busca concluída. {len(resultados)} resultados retornados.")
    log("-" * 60)
    
    # Cria um mapa de resultados por EAN para fácil acesso
    resultados_por_ean = {}
    for resultado in resultados:
        ean_resultado = None
        
        if resultado.get('is_not_found'):
            ean_resultado = resultado.get('ean')
        else:
            for item in resultado.get('items', []):
                if item.get('ean'):
                    ean_resultado = item.get('ean')
                    break
        
        if ean_resultado:
            resultados_por_ean[ean_resultado] = resultado
    
    # Atualiza cada produto
    log("-" * 60)
    log("Processando resultados e atualizando produtos...")
    log("-" * 60)
    
    for produto in produtos:
        ean = produto['ean']
        log(f"Processando EAN: {ean}")
        
        resultado = resultados_por_ean.get(ean)
        
        if not resultado:
            log(f"  -> EAN {ean} não encontrado nos resultados.")
            produto['status'] = 'Não Encontrado'
            produto['ultima_verificacao'] = datetime.now(BR_TZ).isoformat()
            continue
        
        if resultado.get('is_not_found'):
            log(f"  -> EAN {ean} marcado como não encontrado pelo scraper.")
            produto['status'] = 'Não Encontrado'
            produto['ultima_verificacao'] = datetime.now(BR_TZ).isoformat()
            continue
        
        # Extrai preço e nome
        novo_preco, nome = extrair_preco_e_nome(resultado)
        
        # Atualiza o nome se encontrado
        if nome:
            produto['nome'] = nome
            log(f"  -> Nome: {nome}")
        
        # Atualiza o preço
        if novo_preco:
            # Guarda o preço anterior antes de atualizar
            preco_anterior = produto.get('preco_atual')
            
            # Atualiza preços
            produto['preco_anterior'] = preco_anterior
            produto['preco_atual'] = novo_preco
            produto['ultima_verificacao'] = datetime.now(BR_TZ).isoformat()
            produto['status'] = 'Monitorando'
            
            # Adiciona ao histórico
            adicionar_ao_historico(produto, novo_preco)
            
            # Calcula a variação
            if preco_anterior:
                variacao = calcular_variacao(novo_preco, preco_anterior)
                produto['variacao'] = variacao
                
                if variacao > 0:
                    log(f"  -> [SUBIU] R$ {preco_anterior:.2f} -> R$ {novo_preco:.2f} (+{variacao:.1f}%)")
                elif variacao < 0:
                    log(f"  -> [DESCEU] R$ {preco_anterior:.2f} -> R$ {novo_preco:.2f} ({variacao:.1f}%)")
                else:
                    log(f"  -> [SEM ALTERACAO] R$ {novo_preco:.2f}")
            else:
                produto['variacao'] = None
                log(f"  -> Primeiro preço registrado: R$ {novo_preco:.2f}")
        else:
            log(f"  -> Não foi possível extrair o preço.")
            produto['status'] = 'Erro'
            produto['ultima_verificacao'] = datetime.now(BR_TZ).isoformat()
    
    # Salva os produtos atualizados
    salvar_produtos(produtos)
    
    # Resumo final
    log("=" * 60)
    log("RESUMO DA ATUALIZAÇÃO:")
    log("=" * 60)
    
    monitorando = [p for p in produtos if p['status'] == 'Monitorando']
    subiu = [p for p in produtos if p.get('variacao') and p['variacao'] > 0]
    desceu = [p for p in produtos if p.get('variacao') and p['variacao'] < 0]
    erros = [p for p in produtos if p['status'] in ['Erro', 'Não Encontrado']]
    
    log(f"  [OK] Monitorando: {len(monitorando)}")
    log(f"  [SUBIU] Preco Subiu: {len(subiu)}")
    log(f"  [DESCEU] Preco Desceu: {len(desceu)}")
    log(f"  [ERRO] Com Erro/Nao Encontrado: {len(erros)}")
    
    if subiu:
        log("-" * 60)
        log("PRODUTOS COM PREÇO EM ALTA:")
        for p in subiu:
            log(f"  • {p['nome'] or p['ean']}: R$ {p['preco_atual']:.2f} (+{p['variacao']:.1f}%)")
    
    if desceu:
        log("-" * 60)
        log("PRODUTOS COM PREÇO EM BAIXA:")
        for p in desceu:
            log(f"  • {p['nome'] or p['ean']}: R$ {p['preco_atual']:.2f} ({p['variacao']:.1f}%)")
    
    log("=" * 60)
    log("Atualização concluída!")
    log("=" * 60)


if __name__ == "__main__":
    atualizar_produtos()
