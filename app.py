import streamlit as st
import pandas as pd
import json
import os
import io
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÕES ---
PRODUTOS_FILE = "produtos.json"

# --- ESTILO CSS CUSTOMIZADO ---
st.markdown("""
<style>
    /* Cores e tema */
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --success-color: #00c853;
        --warning-color: #ff9800;
        --danger-color: #f44336;
    }
    
    /* Cards modernos */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }
    
    .metric-card h3 {
        font-size: 2.5rem;
        margin: 0;
        font-weight: 700;
    }
    
    .metric-card p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 0.9rem;
    }
    
    /* Formulário estilizado */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        padding: 12px 16px;
        font-size: 1.1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
    }
    
    /* Botões */
    .stButton > button {
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    
    /* Tabela */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Header do card de cadastro */
    .cadastro-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .cadastro-header h2 {
        margin: 0;
        font-size: 1.8rem;
    }
    
    .cadastro-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Badge de status */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .status-monitorando { background: #e8f5e9; color: #2e7d32; }
    .status-pendente { background: #fff3e0; color: #ef6c00; }
    .status-erro { background: #ffebee; color: #c62828; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE PERSISTÊNCIA ---
def carregar_produtos() -> list:
    """Carrega a lista de produtos do arquivo JSON."""
    if not os.path.exists(PRODUTOS_FILE):
        return []
    try:
        with open(PRODUTOS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("produtos", [])
    except (json.JSONDecodeError, IOError):
        return []

def salvar_produtos(produtos: list):
    """Salva a lista de produtos no arquivo JSON."""
    with open(PRODUTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"produtos": produtos}, f, ensure_ascii=False, indent=2)

def adicionar_produto(ean: str) -> tuple[bool, str]:
    """Adiciona um novo produto à lista de monitoramento."""
    produtos = carregar_produtos()
    
    if any(p['ean'] == ean for p in produtos):
        return False, f"O EAN {ean} já está sendo monitorado."
    
    novo_produto = {
        "ean": ean,
        "nome": "",
        "preco_atual": None,
        "preco_anterior": None,
        "variacao": None,
        "ultima_verificacao": None,
        "status": "Pendente",
        "historico": []
    }
    
    produtos.append(novo_produto)
    salvar_produtos(produtos)
    return True, f"Produto {ean} adicionado com sucesso!"

def adicionar_produtos_em_lote(eans: list[str]) -> tuple[int, int, list[str]]:
    """Adiciona múltiplos produtos. Retorna (adicionados, duplicados, erros)."""
    produtos = carregar_produtos()
    eans_existentes = {p['ean'] for p in produtos}
    
    adicionados = 0
    duplicados = 0
    erros = []
    
    for ean in eans:
        ean = ean.strip()
        if not ean:
            continue
        if not ean.isdigit():
            erros.append(f"{ean} (não é numérico)")
            continue
        if ean in eans_existentes:
            duplicados += 1
            continue
        
        novo_produto = {
            "ean": ean,
            "nome": "",
            "preco_atual": None,
            "preco_anterior": None,
            "variacao": None,
            "ultima_verificacao": None,
            "status": "Pendente",
            "historico": []
        }
        produtos.append(novo_produto)
        eans_existentes.add(ean)
        adicionados += 1
    
    salvar_produtos(produtos)
    return adicionados, duplicados, erros

def remover_produto(ean: str) -> bool:
    """Remove um produto da lista de monitoramento."""
    produtos = carregar_produtos()
    produtos_filtrados = [p for p in produtos if p['ean'] != ean]
    
    if len(produtos_filtrados) < len(produtos):
        salvar_produtos(produtos_filtrados)
        return True
    return False

def exportar_para_excel(produtos: list) -> bytes:
    """Exporta a lista de produtos para Excel."""
    df_data = []
    for p in produtos:
        df_data.append({
            "EAN": p['ean'],
            "Nome": p.get('nome', ''),
            "Preço Atual": p.get('preco_atual'),
            "Preço Anterior": p.get('preco_anterior'),
            "Variação (%)": p.get('variacao'),
            "Última Verificação": p.get('ultima_verificacao'),
            "Status": p.get('status')
        })
    
    df = pd.DataFrame(df_data)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output.getvalue()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Monitor de Preços - Pague Menos",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- HEADER ---
st.markdown("""
<div style="text-align: center; padding: 1rem 0 2rem 0;">
    <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem; margin-bottom: 0.5rem;">
        💊 Monitor de Preços
    </h1>
    <p style="color: #666; font-size: 1.1rem;">Pague Menos • Ferramenta de Pricing Inteligente</p>
</div>
""", unsafe_allow_html=True)

# --- BOTÃO DE ATUALIZAÇÃO ---
col_update, col_space = st.columns([1, 3])
with col_update:
    if st.button("🔄 Atualizar Preços", type="primary", use_container_width=True):
        with st.spinner("Atualizando preços... Isso pode levar alguns segundos."):
            try:
                from atualizador import atualizar_produtos
                atualizar_produtos()
                st.success("✅ Preços atualizados com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

# --- MÉTRICAS ---
produtos = carregar_produtos()

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

total_monitorado = len(produtos)
pendentes = len([p for p in produtos if p['status'] == 'Pendente'])
preco_subiu = len([p for p in produtos if p.get('variacao') and p['variacao'] > 0])
preco_desceu = len([p for p in produtos if p.get('variacao') and p['variacao'] < 0])

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>{total_monitorado}</h3>
        <p>📦 Total Monitorado</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);">
        <h3>{pendentes}</h3>
        <p>⏳ Pendentes</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);">
        <h3>{preco_subiu}</h3>
        <p>📈 Preço Subiu</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);">
        <h3>{preco_desceu}</h3>
        <p>📉 Preço Desceu</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- ABAS PRINCIPAIS ---
tab_cadastro, tab_tabela, tab_graficos = st.tabs(["➕ Cadastrar Produtos", "📋 Tabela de Produtos", "📈 Gráficos"])

# === ABA CADASTRO (PRIMEIRA AGORA) ===
with tab_cadastro:
    st.markdown("""
    <div class="cadastro-header">
        <h2>➕ Adicionar Produtos ao Monitoramento</h2>
        <p>Cadastre produtos informando o código de barras (EAN)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Duas colunas para os métodos de cadastro
    col_individual, col_lote = st.columns(2)
    
    # --- CADASTRO INDIVIDUAL ---
    with col_individual:
        st.markdown("### 🔢 Cadastro Individual")
        st.markdown("Digite um código de barras por vez")
        
        with st.form("form_cadastro", clear_on_submit=True):
            ean_input = st.text_input(
                "Código EAN",
                placeholder="Ex: 7891234567890",
                max_chars=13,
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("✅ Cadastrar Produto", use_container_width=True, type="primary")
            
            if submitted:
                if not ean_input or not ean_input.strip():
                    st.error("❌ Por favor, informe o código EAN.")
                elif not ean_input.isdigit():
                    st.error("❌ O EAN deve conter apenas números.")
                else:
                    sucesso, mensagem = adicionar_produto(ean_input.strip())
                    if sucesso:
                        st.success(f"✅ {mensagem}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {mensagem}")
    
    # --- CADASTRO EM LOTE ---
    with col_lote:
        st.markdown("### 📁 Cadastro em Lote")
        st.markdown("Faça upload de arquivo com múltiplos EANs")
        
        uploaded_file = st.file_uploader(
            "Selecione arquivo .txt ou .csv",
            type=['txt', 'csv'],
            help="Um EAN por linha",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                content = uploaded_file.getvalue().decode('utf-8')
                eans = content.strip().split('\n')
                eans = [ean.strip().replace(',', '') for ean in eans if ean.strip()]
                
                st.info(f"📋 **{len(eans)} EANs** encontrados no arquivo")
                
                with st.expander("👀 Ver EANs do arquivo"):
                    st.code('\n'.join(eans[:20]) + ('\n...' if len(eans) > 20 else ''))
                
                if st.button("📥 Importar Todos os EANs", type="primary", use_container_width=True):
                    adicionados, duplicados, erros = adicionar_produtos_em_lote(eans)
                    
                    if adicionados > 0:
                        st.success(f"✅ **{adicionados}** produtos adicionados com sucesso!")
                        st.balloons()
                    if duplicados > 0:
                        st.warning(f"⚠️ **{duplicados}** EANs já existiam e foram ignorados")
                    if erros:
                        st.error(f"❌ **{len(erros)}** erros: {', '.join(erros[:5])}")
                    
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {e}")
        else:
            st.markdown("""
            <div style="border: 2px dashed #ccc; border-radius: 12px; padding: 2rem; text-align: center; color: #888;">
                <p style="font-size: 2rem; margin-bottom: 0.5rem;">�</p>
                <p>Arraste um arquivo aqui ou clique para selecionar</p>
            </div>
            """, unsafe_allow_html=True)
    
    # --- DICA ---
    st.markdown("---")
    st.info("""
    💡 **Dica:** Após cadastrar os produtos, clique em **"🔄 Atualizar Preços"** no topo da página 
    para buscar os preços atuais na Pague Menos.
    """)

# === ABA TABELA ===
with tab_tabela:
    if not produtos:
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; background: #f8f9fa; border-radius: 16px;">
            <p style="font-size: 4rem; margin-bottom: 1rem;">📦</p>
            <h3>Nenhum produto cadastrado</h3>
            <p style="color: #666;">Use a aba "Cadastrar Produtos" para adicionar seus primeiros produtos.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # --- FILTROS ---
        st.markdown("### 🔍 Filtros")
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        with col_filtro1:
            status_options = ["Todos"] + list(set(p['status'] for p in produtos))
            filtro_status = st.selectbox("Status", status_options)
        
        with col_filtro2:
            filtro_variacao = st.selectbox("Variação", ["Todos", "📈 Subiu", "📉 Desceu", "➡️ Sem alteração"])
        
        with col_filtro3:
            ordenar_por = st.selectbox("Ordenar por", ["EAN", "Nome", "Maior Variação", "Menor Variação", "Preço Atual"])
        
        # Aplica filtros
        produtos_filtrados = produtos.copy()
        
        if filtro_status != "Todos":
            produtos_filtrados = [p for p in produtos_filtrados if p['status'] == filtro_status]
        
        if filtro_variacao == "📈 Subiu":
            produtos_filtrados = [p for p in produtos_filtrados if p.get('variacao') and p['variacao'] > 0]
        elif filtro_variacao == "📉 Desceu":
            produtos_filtrados = [p for p in produtos_filtrados if p.get('variacao') and p['variacao'] < 0]
        elif filtro_variacao == "➡️ Sem alteração":
            produtos_filtrados = [p for p in produtos_filtrados if p.get('variacao') == 0]
        
        # Aplica ordenação
        if ordenar_por == "Maior Variação":
            produtos_filtrados.sort(key=lambda x: x.get('variacao') or 0, reverse=True)
        elif ordenar_por == "Menor Variação":
            produtos_filtrados.sort(key=lambda x: x.get('variacao') or 0)
        elif ordenar_por == "Preço Atual":
            produtos_filtrados.sort(key=lambda x: x.get('preco_atual') or 0, reverse=True)
        elif ordenar_por == "Nome":
            produtos_filtrados.sort(key=lambda x: x.get('nome') or '')
        
        st.markdown("---")
        
        # --- TABELA ---
        st.markdown(f"### 📋 Produtos ({len(produtos_filtrados)} de {len(produtos)})")
        
        df_data = []
        for p in produtos_filtrados:
            preco_atual = f"R$ {p['preco_atual']:.2f}" if p.get('preco_atual') else "—"
            preco_anterior = f"R$ {p['preco_anterior']:.2f}" if p.get('preco_anterior') else "—"
            
            variacao_display = "—"
            if p.get('variacao') is not None:
                var = p['variacao']
                if var > 0:
                    variacao_display = f"📈 +{var:.1f}%"
                elif var < 0:
                    variacao_display = f"📉 {var:.1f}%"
                else:
                    variacao_display = "➡️ 0%"
            
            data_formatada = "—"
            if p.get('ultima_verificacao'):
                try:
                    dt = datetime.fromisoformat(p['ultima_verificacao'])
                    data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    data_formatada = p['ultima_verificacao']
            
            status_icons = {"Pendente": "⏳", "Monitorando": "👁️", "Erro": "❌", "Não Encontrado": "❓"}
            status_display = f"{status_icons.get(p['status'], '')} {p['status']}"
            
            df_data.append({
                "EAN": p['ean'],
                "Nome": p['nome'] if p['nome'] else "—",
                "Preço Atual": preco_atual,
                "Preço Anterior": preco_anterior,
                "Variação": variacao_display,
                "Última Verificação": data_formatada,
                "Status": status_display
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # --- AÇÕES ---
        st.markdown("---")
        col_exp, col_remove = st.columns(2)
        
        with col_exp:
            st.markdown("### 📥 Exportar Dados")
            excel_bytes = exportar_para_excel(produtos_filtrados)
            st.download_button(
                label="📥 Baixar Excel",
                data=excel_bytes,
                file_name=f"monitoramento_precos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_remove:
            st.markdown("### 🗑️ Remover Produto")
            ean_para_remover = st.selectbox(
                "Selecione o EAN",
                options=[p['ean'] for p in produtos],
                format_func=lambda x: f"{x} - {next((p['nome'] for p in produtos if p['ean'] == x), 'Sem nome')}",
                label_visibility="collapsed"
            )
            if st.button("🗑️ Remover Produto", type="secondary", use_container_width=True):
                if remover_produto(ean_para_remover):
                    st.success(f"✅ Produto {ean_para_remover} removido!")
                    st.rerun()

# === ABA GRÁFICOS ===
with tab_graficos:
    produtos_com_historico = [p for p in produtos if p.get('historico') and len(p['historico']) > 0]
    
    if not produtos_com_historico:
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; background: #f8f9fa; border-radius: 16px;">
            <p style="font-size: 4rem; margin-bottom: 1rem;">📊</p>
            <h3>Nenhum histórico disponível</h3>
            <p style="color: #666;">Execute o atualizador mais vezes para acumular dados de histórico.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 📈 Histórico de Preços")
        
        produto_selecionado = st.selectbox(
            "Selecione um produto",
            options=produtos_com_historico,
            format_func=lambda x: f"{x['ean']} - {x['nome'] or 'Sem nome'}"
        )
        
        if produto_selecionado and produto_selecionado.get('historico'):
            historico = produto_selecionado['historico']
            
            df_hist = pd.DataFrame(historico)
            df_hist['data'] = pd.to_datetime(df_hist['data'])
            df_hist = df_hist.sort_values('data')
            
            fig = px.line(
                df_hist, 
                x='data', 
                y='preco',
                title=f"📈 {produto_selecionado['nome'] or produto_selecionado['ean']}",
                labels={'data': 'Data', 'preco': 'Preço (R$)'},
                markers=True
            )
            fig.update_layout(
                xaxis_title="Data",
                yaxis_title="Preço (R$)",
                hovermode="x unified",
                template="plotly_white"
            )
            fig.update_traces(line_color='#667eea', marker_size=10, line_width=3)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Estatísticas
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            precos = [h['preco'] for h in historico]
            
            with col_stat1:
                st.metric("Preço Atual", f"R$ {precos[-1]:.2f}")
            with col_stat2:
                st.metric("Mínimo", f"R$ {min(precos):.2f}")
            with col_stat3:
                st.metric("Máximo", f"R$ {max(precos):.2f}")
            with col_stat4:
                st.metric("Média", f"R$ {sum(precos)/len(precos):.2f}")

# --- RODAPÉ ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 1rem; color: #888;">
    💊 <strong>Monitor de Preços</strong> • Pague Menos • Ferramenta de Pricing
</div>
""", unsafe_allow_html=True)
