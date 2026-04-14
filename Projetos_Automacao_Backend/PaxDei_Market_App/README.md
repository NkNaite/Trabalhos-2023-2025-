# Pax Dei Market Analysis Tool

A Python-based toolset for analyzing crafting profitability in the game *Pax Dei*. This project automates the process of fetching market prices, building a recipe catalog, and calculating the profit margins (spread) for various crafting recipes.

## 📁 Project Structure

```
d:/PaxDei_Tool/
├── src/                # Core analysis logic
│   ├── advisor.py      # UNIFIED CLI ENTRY POINT
│   ├── modules/        # Helper libraries (market, crafting, logistics, sales_tracker)
│   └── relatorios/     # Generated reports and ad-hoc analysis
├── data/               # Data storage (input/output)
│   ├── catalogo_manufatura.json # Generated recipe catalog
│   ├── selene_latest.parquet    # Master Price File (Parquet)
│   └── history/                 # Daily Snapshots (year=YYYY/month=MM)
├── scripts/            # Utility scripts
│   └── sync_data.py    # Syncs data from Hugging Face
└── start_dashboard.bat # Shortcut to update data and start dashboard
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.13** (See `docs/Parametros.md` for interpreter path).
- **pandas**, **pyarrow/fastparquet** (for Parquet support).

## 🛠️ Usage Guide

### Step 1: Data Synchronization

To get the latest market data from the community repository (Hugging Face):

```bash
python scripts/sync_data.py
```
*(Alternative: Run `start_dashboard.bat`)*

### Step 2: Consultas e Inteligência (Unified Advisor)

Utilize `src/advisor.py` para todas as análises.

#### 1. Inteligência de Mercado (`market`)
*   **Histórico de Item:**
    ```bash
    python src/advisor.py market --history "Iron Ingot"
    ```
*   **Liquidez (O que vendeu recentemente):**
    ```bash
    python src/advisor.py market --liquidity
    ```
*   **Top Produtores:**
    ```bash
    python src/advisor.py market --sellers "Antlers"
    ```
*   **Análise de Stack (Perda de Valor):**
    ```bash
    python src/advisor.py market --analyze-stacks "Iron Ingot" --min-stack 20
    ```

#### 2. Crafting e Manufatura (`crafting` / `recipe`)
*   **Lucratividade (Spread):**
    ```bash
    python src/advisor.py crafting --top 10
    ```
*   **Raio-X de Receita (Detalhado):**
    ```bash
    python src/advisor.py recipe "Iron Ingot" --recursive
    ```

#### 3. Logística e Rotas (`logistics`)
*   **Scan de Rotas (Arbitragem + Histórico):**
    ```bash
    python src/advisor.py logistics --scan
    ```
*   **Oportunidades de Arbitragem:**
    ```bash
    python src/advisor.py logistics --arbitrage
    ```
*   **Calcular Rota Segura:**
    ```bash
    python src/advisor.py logistics --route "Llydaw" "Merrie"
    ```

#### 4. Tracker de Vendas e Lucro (`sales`)
*   **Passo 1: Identificar seu ID (Configuração Inicial):**
    Publique um item com preço único (ex: 888 Gold) e use o comando:
    ```bash
    python src/advisor.py sales --identify "Item Name" 888
    ```

*   **Passo 2: Monitorar Vendas e Lucro:**
    Visualize vendas, receita bruta e lucro líquido (com desconto de taxas de 5%):
    ```bash
    python src/advisor.py sales
    ```
    *Para filtrar por item especifico:*
    ```bash
    python src/advisor.py sales --item "Bold Winter Stout"
    ```

#### 5. Shopping List Scanner (Novo)
*   **Escanear Lista de Compras:**
    Compare preços da sua lista de estoque em uma região contra outra (ou global):
    ```bash
    python src/advisor.py shopping --list Guia_Estoque_Crafting.md --zone "Langres" --target "Aven"
    ```
    *Isso busca itens da lista à venda em Langres com preço abaixo da mediana de Aven.*

## 🔄 Ciclo Diário de Execução

1.  **Coleta Automática**: Rodar `scripts/sync_data.py`.
2.  **Análise**: Usar o `advisor.py` para tomar decisões de compra/crafting.
3.  **Vendas**: Checar `advisor.py sales` para ver o lucro do dia.

## 📊 Understanding the Output

### Profitability (`analise_disparidade.csv`)
- **Produto**: The crafted item name.
- **Spread**: Profit amount (`Preco_Venda - Custo_Manufatura`).
- **Margem_Perc**: Profit margin percentage.

### Liquidity (`liquidez_diaria.csv`)
- **Units_Sold**: Number of listings that disappeared (sold/expired).
- **Top_Zone**: The zone with the highest volume of sales for this item.

## 🛡️ Failsafe Protocol (For Developers/AI)
**ATTENTION:** To prevent token limit errors during autonomous execution:
1.  **Trust Tool Output:** If a command runs successfully (Exit Code 0), do not double-check manually. Assume the data is valid.
2.  **No Repeats:** Do not perform "validation loops" (e.g., listing a file, then reading it, then listing it again).
3.  **Direct Action:** Prefer executing the analysis command (`advisor.py`) over manual script creation or file introspection.

