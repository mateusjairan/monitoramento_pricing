import requests
import json
import base64
import time
import pandas as pd
import io
from urllib.parse import quote
import re
import uuid
import os
from typing import List, Dict, Any, Optional
# --- CONFIGURAÇÕES ---
PRODUTOS_POR_PAGINA = 50  # O padrão da VTEX é 50, usar 51 pode causar comportamento inesperado.
# O site mudou a API de busca. O User-Agent e a x-api-key agora são cruciais.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
    'x-api-key': 'Yt1tDH9WNx5pmTXrBPBFH8mHAMJ5Gbb3dbSdu12d'
}
API_URL_BASE_NOVA = "https://prod.apipmenos.com/buscacatalogo/api/searchurl"
API_URL_PRODUCT_DETAIL = "https://www.paguemenos.com.br/_v/segment/graphql/v1?workspace=master&maxAge=short&appsEtag=remove&domain=store&locale=pt-BR&operationName=Product&variables=%7B%7D"

# --- SESSÃO DE REQUISIÇÃO ---
# Cria uma única sessão para reutilizar conexões TCP, melhorando o desempenho.
session = requests.Session()
session.headers.update(HEADERS)
# --- FIM DAS CONFIGURAÇÕES ---

def load_departments() -> Dict[str, Any]:
    """
    Carrega todos os arquivos JSON de departamentos da pasta 'departments'.
    Retorna um dicionário onde a chave é o slug do departamento e o valor é o conteúdo do JSON.
    """
    departments_data = {}
    if not os.path.exists('departments'):
        print("Aviso: A pasta 'departments' não foi encontrada.")
        return departments_data

    for filename in os.listdir('departments'):
        if filename.endswith('.json'):
            filepath = os.path.join('departments', filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    department_slug = data.get("department_slug")
                    if department_slug:
                        departments_data[department_slug] = data
                    else:
                        print(f"Aviso: O arquivo {filename} não contém a chave 'department_slug'.")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Erro ao carregar o arquivo do departamento {filename}: {e}")
    return departments_data

def get_all_targets(log_callback=print) -> List[Dict[str, str]]:
    """
    Carrega todos os departamentos e extrai uma lista plana de todos os alvos
    (categorias e subcategorias) disponíveis para scraping.

    :param log_callback: Função para registrar mensagens de log.
    :return: Uma lista de dicionários, onde cada dicionário é um alvo de busca.
    """
    log_callback("Carregando todos os alvos de todos os departamentos...")
    all_targets = []
    departments = load_departments()

    for dept_slug, dept_data in departments.items():
        # Adiciona as categorias do departamento
        if 'categories' in dept_data and isinstance(dept_data['categories'], list):
            all_targets.extend(dept_data['categories'])
        
        # Adiciona as subcategorias do departamento
        if 'subcategories' in dept_data and isinstance(dept_data['subcategories'], list):
            all_targets.extend(dept_data['subcategories'])
        
        # Adiciona os alvos de marca (ex: departamento 'Cuidado e Beleza')
        if 'targets' in dept_data and isinstance(dept_data['targets'], list):
            all_targets.extend(dept_data['targets'])

    log_callback(f"Total de {len(all_targets)} alvos (categorias/subcategorias) carregados.")
    return all_targets


def fazer_requisicao_api_vtex(variables: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Monta a URL e faz a requisição para a API GraphQL da VTEX.
    Retorna a lista de produtos da página ou None em caso de erro.
    """
    url_base = "https://www.paguemenos.com.br/_v/segment/graphql/v1?workspace=master&maxAge=short&appsEtag=remove&domain=store&locale=pt-BR&operationName=productSearchV3&variables=%7B%7D"
    try:
        variables_str = json.dumps(variables)
        base64_variables = base64.b64encode(variables_str.encode('utf-8')).decode('utf-8')

        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "efcfea65b452e9aa01e820e140a5b4a331adfce70470d2290c08bc4912b45212",
                "sender": "vtex.store-resources@0.x",
                "provider": "vtex.search-graphql@0.x"
            },
            "variables": base64_variables
        }

        url_final = f"{url_base}&extensions={quote(json.dumps(extensions))}"

        response = session.get(url_final)
        response.raise_for_status()
        payload = response.json()

        data = payload.get('data', {})
        product_search = data.get('productSearch', {})
        return product_search.get('products', [])

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição (API VTEX): {e}") # Loga apenas no console do servidor
        return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar a resposta JSON (API VTEX): {e}") # Loga apenas no console do servidor
        return None


def fazer_requisicao_api_proxy(search_term: str, page: int, is_ean: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Monta a URL e faz a requisição para a API de busca intermediária (proxy) da Pague Menos.
    Retorna None em caso de erro.
    """
    try:
        # A API foi atualizada para usar 'terms' tanto para busca de EAN quanto para caminhos de categoria (path).
        # O parâmetro 'path' foi descontinuado.
        inner_url_params = f"apikey=farmacia-paguemenos&terms={search_term}&page={page}&resultsperpage={PRODUTOS_POR_PAGINA}&showonlyavailable=false&allowredirect=true"
        inner_url = f"/engage/search/v3/search?{inner_url_params}"

        params = {
            "salesChannel": "1",
            "company": "1",
            "url": inner_url,
            "deviceId": str(uuid.uuid4()), # Gera um deviceId aleatório
            "source": "mobile"
        }

        response = session.get(API_URL_BASE_NOVA, params=params)
        response.raise_for_status()
        payload = response.json()

        # A API mudou a estrutura da resposta. Os produtos agora estão na chave 'data'.
        return payload.get('data', [])

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar a resposta JSON: {e}")
        return None

def fetch_product_details(product_id: str, log_callback=print) -> Optional[Dict[str, Any]]:
    """
    Busca os detalhes completos de um único produto usando seu ID.
    Esta função usa a operação 'Product' que retorna dados mais ricos.
    """
    try:
        variables = {"identifier": {"field": "id", "value": product_id}}
        variables_str = json.dumps(variables)
        base64_variables = base64.b64encode(variables_str.encode('utf-8')).decode('utf-8')

        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "114aa626a0d49a5aae73229b9056bcc63556c88d76b629531e9a5e7344104451",
                "sender": "paguemenos.product-card@0.x",
                "provider": "vtex.search-graphql@0.x"
            },
            "variables": base64_variables
        }

        url_final = f"{API_URL_PRODUCT_DETAIL}&extensions={quote(json.dumps(extensions))}"

        response = session.get(url_final)
        response.raise_for_status()
        payload = response.json()

        return payload.get('data', {}).get('product')

    except requests.exceptions.RequestException as e:
        log_callback(f"  -> Erro na requisição de detalhes para o produto ID {product_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        log_callback(f"  -> Erro ao decodificar JSON de detalhes para o produto ID {product_id}: {e}")
        return None

def enrich_product_summaries(product_summaries: List[Dict[str, Any]], target_name: str, log_callback=print) -> List[Dict[str, Any]]:
    """
    Recebe uma lista de produtos resumidos, busca os detalhes completos de cada um
    e retorna uma lista de produtos enriquecidos.
    """
    enriched_products = []
    for summary in product_summaries:
        product_id = summary.get('productId')
        if not product_id:
            log_callback(f"  -> Aviso: Produto '{summary.get('productName')}' sem ID. Pulando enriquecimento.")
            continue

        # Etapa de enriquecimento: busca os detalhes completos
        detailed_product = fetch_product_details(product_id, log_callback)
        if detailed_product:
            detailed_product['target_name'] = target_name  # Adiciona o contexto da busca
            enriched_products.append(detailed_product)
        
        time.sleep(0.1) # Pequena pausa entre as chamadas de detalhe

    return enriched_products


def scrape_target(target: Dict[str, str], log_callback=print) -> List[Dict[str, Any]]:
    """
    Captura todos os produtos de um alvo (categoria ou subcategoria).

    :param target: Dicionário contendo 'name', 'query', e 'map' do alvo.
    :param log_callback: Função para registrar mensagens de log.
    :return: Uma lista de dicionários, cada um representando um produto.
    """
    all_products = []
    target_name = target.get('name', 'Desconhecido')
    query_path = target.get('query')
    map_param = target.get('map')

    if not query_path or not map_param:
        log_callback(f"Erro: O alvo '{target_name}' não tem 'query' ou 'map' definidos. Pulando.")
        return []

    # A API antiga usa um formato diferente para selectedFacets
    map_keys = map_param.split(',')
    query_values = query_path.split('/')
    selected_facets = [{"key": key, "value": value} for key, value in zip(map_keys, query_values)]

    log_callback(f"--- Iniciando captura para: {target_name} ({query_path}) ---")
    current_page = 0 # A API antiga começa a paginação em 0

    while True:
        variables = {
            "hideUnavailableItems": False, "skusFilter": "ALL_AVAILABLE",
            "simulationBehavior": "default", "installmentCriteria": "MAX_WITHOUT_INTEREST",
            "productOriginVtex": False, "map": map_param, "query": query_path,
            "orderBy": "OrderByScoreDESC",
            "from": current_page * PRODUTOS_POR_PAGINA,
            "to": (current_page + 1) * PRODUTOS_POR_PAGINA - 1,
            "selectedFacets": selected_facets,
            "facetsBehavior": "Static", "categoryTreeBehavior": "default",
            "withFacets": False, "variant": "null-null"
        }

        log_callback(f"Buscando página {current_page + 1} para '{target_name}'...")
        try:
            products_page = fazer_requisicao_api_vtex(variables)
        except Exception as e:
            log_callback(f"  -> Erro crítico ao buscar página para '{target_name}': {e}")
            products_page = None

        if products_page is None:
            log_callback(f"Erro na requisição para '{target_name}'. Encerrando a busca para este alvo.")
            break

        if not products_page:
            log_callback(f"Fim da paginação para '{target_name}'. Todos os produtos foram listados.")
            break

        for product in products_page:
            product['target_name'] = target_name
        all_products.extend(products_page)

        current_page += 1
        time.sleep(1)

    log_callback(f"Captura para '{target_name}' finalizada. Total de {len(all_products)} produtos encontrados.")
    return all_products


def scrape_by_eans(eans: List[str], log_callback=print) -> List[Dict[str, Any]]:
    """
    Captura todos os produtos de uma lista de EANs.

    :param eans: Lista de EANs para buscar.
    :param log_callback: Função para registrar mensagens de log.
    :return: Uma lista de dicionários, cada um representando um produto encontrado.
    """
    all_products_enriched = []
    
    # Separa EANs válidos (13 dígitos) de códigos curtos (provavelmente SKUs internos)
    valid_eans = [ean for ean in eans if len(ean) == 13]
    short_codes = [ean for ean in eans if len(ean) < 13]

    log_callback(f"--- Total de {len(eans)} códigos recebidos: {len(valid_eans)} EANs válidos e {len(short_codes)} códigos curtos. ---")

    # --- 1. Processamento em Lote para EANs Válidos ---
    if not valid_eans:
        log_callback("Nenhum EAN de 13 dígitos para processar em lote.")
    else:
        log_callback(f"--- Processando {len(valid_eans)} EANs válidos em lote ---")
        all_products_enriched.extend(process_eans_in_batch(valid_eans, log_callback))

    # --- 2. Processamento Individual para Códigos Curtos ---
    if not short_codes:
        log_callback("Nenhum código curto para processar individualmente.")
    else:
        log_callback(f"--- Processando {len(short_codes)} códigos curtos individualmente ---")
        all_products_enriched.extend(process_short_codes_individually(short_codes, log_callback))

    log_callback(f"Busca finalizada. Total de {len(all_products_enriched)} resultados processados.")
    return all_products_enriched

def process_eans_in_batch(eans: List[str], log_callback=print) -> List[Dict[str, Any]]:
    """Processa uma lista de EANs válidos (13 dígitos) em lotes."""
    BATCH_SIZE = 48
    results = []
    # Divide a lista de EANs em lotes (chunks)
    ean_batches = [eans[i:i + BATCH_SIZE] for i in range(0, len(eans), BATCH_SIZE)]

    for i, batch in enumerate(ean_batches):
        log_callback(f"Processando lote {i+1}/{len(ean_batches)} com {len(batch)} EANs...")

        # Junta os EANs do lote em uma única string para a API
        search_term = ", ".join(batch)
        products_page = fazer_requisicao_api_proxy(search_term, page=1, is_ean=True)

        if products_page is None:
            log_callback(f"  -> Erro na requisição para o lote {i+1}. Pulando este lote.")
            # Adiciona todos os EANs deste lote como não encontrados
            for ean in batch:
                results.append({'is_not_found': True, 'ean': ean})
            time.sleep(1)
            continue
        
        # Mapeia os produtos encontrados pelo EAN para fácil acesso
        found_products_map = {}
        for product in products_page:
            # O EAN está dentro da lista de 'items' (SKUs)
            for item in product.get('items', []):
                ean_found = item.get('ean')
                # Estratégia 1: Mapeamento direto pelo campo EAN (o mais confiável)
                if ean_found and ean_found in batch:
                    found_products_map[ean_found] = product
                    continue # Já mapeou, vai para o próximo item
                
                # Estratégia 2 (Fallback): Se o EAN estiver vazio, procurar o EAN nos nomes de imagem.
                # Isso resolve casos onde a API retorna o produto, mas o campo 'ean' está em branco.
                if not ean_found:
                    image_urls = [img.get('imageUrl', '') for img in item.get('images', [])]
                    for url in image_urls:
                        # Procura por qualquer um dos EANs do lote na URL da imagem
                        for ean_in_batch in batch:
                            if ean_in_batch in url:
                                # Se encontrar, mapeia esse produto para o EAN correspondente
                                if ean_in_batch not in found_products_map: # Evita sobrescrever um match mais forte
                                    found_products_map[ean_in_batch] = product
                                    log_callback(f"  -> EAN {ean_in_batch} encontrado via fallback (URL da imagem).")
        
        eans_not_found_in_batch = []
        # Processa cada EAN do lote
        for ean in batch:
            if ean in found_products_map:
                product_summary = found_products_map[ean]
                product_name = product_summary.get('productName', 'Nome não encontrado')
                product_id = product_summary.get('productId')

                if product_id:
                    log_callback(f"  -> EAN {ean} encontrado: '{product_name}'. Enriquecendo...")
                    # Usa a função de enriquecimento para buscar os detalhes
                    enriched_products = enrich_product_summaries([product_summary], f"Busca EAN: {ean}", log_callback)
                    if enriched_products:
                        results.extend(enriched_products)
                    else:
                        # Se o enriquecimento falhar, adiciona o produto resumido para não perdê-lo.
                        log_callback(f"  -> Falha ao enriquecer EAN {ean}. Usando dados resumidos.")
                        product_summary['target_name'] = f"Busca EAN: {ean}"
                        results.append(product_summary)
                else:
                    log_callback(f"  -> EAN {ean} encontrado, mas sem ID de produto. Marcando como não encontrado.")
                    eans_not_found_in_batch.append(ean)
            else:
                # EAN não foi encontrado na resposta da API
                log_callback(f"  -> EAN {ean} não encontrado na busca em lote. Tentando busca individual...")
                eans_not_found_in_batch.append(ean)

        # --- Lógica de Retentativa Individual ---
        if eans_not_found_in_batch:
            log_callback(f"  -> Realizando busca individual para {len(eans_not_found_in_batch)} EANs não encontrados no lote.")
            # Usa a função de busca de códigos curtos, que já faz a busca individual
            individual_results = process_short_codes_individually(eans_not_found_in_batch, log_callback)
            results.extend(individual_results)

        time.sleep(1) # Pausa entre os lotes para não sobrecarregar a API
    return results

def process_short_codes_individually(short_codes: List[str], log_callback=print) -> List[Dict[str, Any]]:
    """Processa códigos curtos (SKUs) individualmente, como uma busca por termo."""
    results = []
    for i, code in enumerate(short_codes):
        log_callback(f"Processando código curto {i+1}/{len(short_codes)}: {code}")
        # Usa a mesma função de requisição, para simular uma busca de termo
        products_page = fazer_requisicao_api_proxy(code, page=1, is_ean=True)

        if products_page is None:
            log_callback(f"  -> Erro na requisição para o código '{code}'.")
            results.append({'is_not_found': True, 'ean': code})
            time.sleep(1)
            continue

        found_product = None
        # A API pode retornar múltiplos resultados. Precisamos encontrar o mais relevante.
        # A heurística aqui é procurar um SKU que contenha o código buscado.
        for product in products_page:
            for item in product.get('items', []):
                # Estratégia 1: Verifica se o código corresponde ao EAN ou a uma referência de SKU
                if item.get('ean') == code or (item.get('referenceId') and item.get('referenceId')[0].get('Value') == code):
                    found_product = product
                    break
                
                # Estratégia 2 (Fallback): Procurar o código na URL da imagem
                image_urls = [img.get('imageUrl', '') for img in item.get('images', [])]
                for url in image_urls:
                    if code in url:
                        found_product = product
                        log_callback(f"  -> Código {code} encontrado via fallback (URL da imagem).")
                        break
            if found_product:
                break
        
        if found_product:
            product_name = found_product.get('productName', 'Nome não encontrado')
            product_id = found_product.get('productId')
            log_callback(f"  -> Código {code} encontrado: '{product_name}'. Buscando detalhes...")
            detailed_product = fetch_product_details(product_id, log_callback)
            if detailed_product:
                detailed_product['target_name'] = f"Busca Código: {code}"
                results.append(detailed_product)
            else:
                results.append({'is_not_found': True, 'ean': code})
        else:
            log_callback(f"  -> Nenhum produto correspondente encontrado para o código {code}.")
            results.append({'is_not_found': True, 'ean': code})

        time.sleep(1) # Pausa entre as requisições individuais
    return results

def create_excel_report(results: List[Dict[str, Any]]) -> bytes:
    """
    Extrai os dados dos produtos, gera um arquivo Excel em memória e retorna seus bytes.
    :param results: Lista de resultados (produtos encontrados e marcadores de não encontrados).
    :return: Os bytes do arquivo Excel gerado.
    """
    if not results:
        print("Nenhum produto encontrado para gerar o arquivo Excel.")
        return b""

    excel_data = []
    print(f"\nExtraindo dados de {len(results)} resultados para o arquivo Excel...")

    for product in results:
        # Verifica se é um marcador de produto não encontrado
        if product.get('is_not_found'):
            excel_data.append({
                'EAN': product.get('ean', 'N/A'),
                'Categoria/Subcategoria': 'NÃO ENCONTRADO',
                'Nome': '',
                'Preco Original': '',
                'Preco Oferta': '',
                'Tipo de Oferta': '',
                'Data de Validade': ''
            })
            continue

        try:
            target_name = product.get('target_name', 'N/A')
            # O nome do produto pode estar em 'name' ou 'productName' dependendo da consulta
            base_product_name = product.get('name') or product.get('productName', 'N/A')

            # Um produto pode ter múltiplos SKUs (items), como tamanhos diferentes.
            # Devemos iterar sobre cada um para criar uma linha para cada variação.
            items = product.get('items', [])
            if not items:
                print(f"Aviso: Produto '{base_product_name}' (ID: {product.get('productId')}) não possui SKUs ('items'). Pulando.")
                continue
            
            # Itera sobre cada SKU (item) do produto
            for item in items:
                # O nome completo do SKU (ex: com o tamanho) é mais específico
                sku_name = item.get('name') or item.get('nameComplete') or base_product_name
                if sku_name and isinstance(sku_name, str):
                    sku_name = re.sub(r'<.*?>', '', sku_name)
                
                ean = item.get('ean', 'N/A')
                if not ean:  # Garante que o EAN seja 'N/A' se estiver vazio
                    ean = 'N/A'

                offer_price = 0.0
                original_price = 0.0
                offer_type = 'N/A'
                
                # A data de validade pode vir como 'releaseDate' (API antiga) ou não vir (API nova)
                release_date_raw = product.get('releaseDate')
                release_date = 'N/A'
                if release_date_raw and release_date_raw.isdigit():
                     # Converte de milissegundos para um formato legível
                    release_date = pd.to_datetime(int(release_date_raw), unit='ms').strftime('%d/%m/%Y')
                
                # Procura pelo vendedor com uma oferta válida dentro do SKU atual
                valid_offer = None
                for seller in item.get('sellers', []):
                    offer = seller.get('commertialOffer')
                    if offer:
                        # A API de busca resumida não tem 'AvailableQuantity'.
                        # Usamos a presença de um preço > 0 como indicador de disponibilidade.
                        is_available_new_api = 'AvailableQuantity' not in offer and offer.get('price', 0) > 0
                        is_available_old_api = offer.get('AvailableQuantity', 0) > 0
                        if is_available_old_api or is_available_new_api:
                            valid_offer = offer
                        break  # Encontrou a primeira oferta válida, pode parar

                if valid_offer:
                    # Extrai os preços brutos da API
                    # A chave do preço pode ser 'price' (API nova) ou 'Price' (API antiga).
                    # O código agora tenta a chave em minúsculo primeiro.
                    offer_price_raw = valid_offer.get('price') or valid_offer.get('Price', 0.0)
                    original_price_raw = valid_offer.get('listPrice') or valid_offer.get('ListPrice') or offer_price_raw

                    # Arredonda os preços para 2 casas decimais para corrigir imprecisões de ponto flutuante
                    offer_price = round(offer_price_raw, 2)
                    original_price = round(original_price_raw, 2)

                    if original_price < offer_price:
                        original_price = offer_price
                    offer_type = next((t.get('name', 'Oferta') for t in valid_offer.get('teasers', [])), 'N/A')

                # Se o preço for 0.0, define como "sem preco". Caso contrário, mantém o valor.
                final_original_price = "sem preco" if original_price == 0.0 else original_price
                final_offer_price = "sem preco" if offer_price == 0.0 else offer_price

                excel_data.append({
                    'EAN': ean,
                    'Categoria/Subcategoria': target_name,
                    'Nome': sku_name,
                    'Preco Original': final_original_price,
                    'Preco Oferta': final_offer_price,
                    'Tipo de Oferta': offer_type,
                    'Data de Validade': release_date
                })

        except (IndexError, KeyError, TypeError) as e:
            print(f"Aviso: Não foi possível processar completamente o produto ID: {product.get('productId', 'N/A')}. Erro: {e}")

    df = pd.DataFrame(excel_data)
    # Garante que o DataFrame não esteja vazio antes de reordenar as colunas
    if not df.empty:
        df = df[['EAN', 'Categoria/Subcategoria', 'Nome', 'Preco Original', 'Preco Oferta', 'Tipo de Oferta', 'Data de Validade']]
    
    # Cria o arquivo Excel em um buffer de memória
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0) # Retorna ao início do buffer para leitura
    
    print("Arquivo Excel gerado em memória com sucesso.")
    return output.getvalue()