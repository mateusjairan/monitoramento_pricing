# 💊 Monitor de Preços - Pague Menos

Ferramenta de pricing para monitorar variações de preços de produtos na farmácia Pague Menos.

## 📋 Funcionalidades

- ✅ Cadastro de produtos por EAN (código de barras)
- ✅ Monitoramento de variações de preço (subiu/desceu)
- ✅ Histórico de preços com gráficos
- ✅ Filtros e ordenação
- ✅ Exportação para Excel
- ✅ Cadastro em lote (upload de .txt/.csv)
- ✅ Atualização automática via GitHub Actions
- ✅ Notificações via Telegram (opcional)

## 🚀 Instalação

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/monitor_pg_menos.git
cd monitor_pg_menos

# Instale as dependências
pip install streamlit pandas requests openpyxl plotly
```

## 📁 Estrutura do Projeto

```
monitor_pg_menos/
├── app.py              # Dashboard Streamlit
├── atualizador.py      # Script de atualização de preços
├── scraper_core.py     # Módulo de scraping (API Pague Menos)
├── notificador.py      # Módulo de notificações Telegram
├── produtos.json       # Banco de dados local
├── .github/
│   └── workflows/
│       └── monitor-precos.yml  # Automação GitHub Actions
└── dispose/            # Arquivos legados (não utilizados)
```

## 💻 Como Usar

### Dashboard (Interface Visual)

```bash
streamlit run app.py
```

Acesse: http://localhost:8501

### Atualização Manual de Preços

```bash
python atualizador.py
```

## ⚙️ Automação com GitHub Actions

O workflow executa automaticamente a cada 6 horas e faz commit das alterações.

**Configuração necessária:**
1. Vá em `Settings` → `Actions` → `General`
2. Em "Workflow permissions", selecione **"Read and write permissions"**

**Executar manualmente:** `Actions` → `Monitoramento de Preços` → `Run workflow`

## 📱 Notificações Telegram (Opcional)

1. Crie um bot no Telegram via [@BotFather](https://t.me/BotFather)
2. Crie o arquivo `config_telegram.json`:

```json
{
  "bot_token": "SEU_TOKEN_AQUI",
  "chat_id": "SEU_CHAT_ID"
}
```

## 📊 Schema do Produto

```json
{
  "ean": "7891234567890",
  "nome": "Nome do Produto",
  "preco_atual": 29.90,
  "preco_anterior": 32.50,
  "variacao": -8.0,
  "status": "Monitorando",
  "historico": [
    {"data": "2025-12-23T13:00:00", "preco": 29.90}
  ]
}
```

## 📝 Licença

MIT License
