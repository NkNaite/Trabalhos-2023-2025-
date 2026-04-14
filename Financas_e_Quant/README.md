# 📈 Finanças Quantitativas e Engenharia de Portfólio

Este reduto laboratorial abriga a intersecção entre **Matemática Avançada, Estatística e o Mercado Financeiro**. Consiste na implementação sistemática de modelos preditivos, precificação teórica de risco e backtests algorítmicos.

O foco central aqui é transcender a mera análise "gráfica" em favor da lógica assíncrona orientada a dados *Intraday*, otimizadores Convexos e *Digital Signal Processing* (Processamento de Sinais Financeiros).

---

## 🏗️ Estrutura Analítica

O ambiente foi lapidado em três frentes de altíssima complexidade (arquitetadas em cadernos sequenciais):

### 1️⃣ `01_Gestao_Risco_e_Otimizacao_Portfolio.ipynb`
* **Disciplina**: *Teoria Moderna de Portfólio & Análise de Volatilidade*
* **Objetivo**: Demonstrar capacidade de avaliar o Risco Sistêmico (via matrizes de volatilidade/covariância sobre Sérias Temporais financeiras) e entregar pesos operacionais através do algoritmo matemático Clássico de Balanceamento de Markowitz.
* Esta é a fundação para lidar com **Alocação de Ativos e Wealth Management**.

### 2️⃣ `02_Backtesting_e_Estrategias_Quantitativas.ipynb`
* **Disciplina**: *Algorithmic Trading & Dados Tick-Level*
* **Objetivo**: Uma demonstração brutal de fluxo contínuo de dados extraídos diretos da API YFinance (`Tick/Intraday` de até 2 anos).
* **Stack**: Operacionalizamos bibliotecas de tempo, *numpy* vetorizado e lógicas complexas de entrada e saída. Este código baseia-se num desafio estrutural de backtesting da equipe *Itaú Quant*, gerando execuções de estratégias sistemáticas que podem ser modeladas por cruzamentos direcionais puros ou quebras estocásticas.

### 3️⃣ `03_Processamento_Sinais_Fourier_Paparazi.ipynb`
* **Disciplina**: *Engenharia Preditiva e Filtragem de Transformadas (O Algoritmo Paparazi)*
* **Objetivo**: O desfecho da jornada Quant. Aqui é apresentada uma tese algorítmica onde utilizamos matemática contínua (fortemente inspirada no conceito matricial das **Transformadas de Fourier**) para destilar os ruídos intraday das cotações em "Ondas e Harmonicos puros".
* Transformamos a linguagem de compilação da corretora (Pine Script) em lógicas de *Trigonometria Arctangencial* usando NumPy. As matrizes isolam as tangentes do ciclo de mercado e projetam as janelas preditivas. Isso consolida não só sua aptidão teórica de finanças, mas também sólida base em *Digital Signal Processing (DSP)* para a busca de Alpha.

---

## 🚀 Como Executar
1. Instale o ambiente quantitativo básico: `pip install -q yfinance ta pandas numpy`.
2. O caderno **01** processará suas teses de investimento de médio-prazo com simulação de Monte Carlo ou Força Bruta Clássica.
3. O **02** fará o bypass pesado das coletas intraday do Yahoo Finance (execute com moderação para respeitar os headers da API).
4. O **03 (Fourier Signal Processing)** aguarda um dump rápido em CSV na mesma raiz (`IVVB11_2025.csv`) para calcular e destilar as matrizes inversas!
