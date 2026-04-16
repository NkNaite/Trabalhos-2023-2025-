import pandas as pd
import yfinance as yf
import json
import os

# Configurações
SYMBOL = "IVVB11.SA"
OUTPUT_HTML = "analise_ivvb11_2025.html"
OUTPUT_CSV = "IVVB11_2025_Paparazi.csv"

def get_data():
    """Tenta ler o CSV local ou baixa do Yahoo Finance caso não exista."""
    csv_file = "IVVB11_2025.csv"
    if os.path.exists(csv_file):
        print(f"Lendo dados de {csv_file}...")
        df = pd.read_csv(csv_file)
    else:
        print(f"CSV não encontrado. Baixando dados de {SYMBOL}...")
        df = yf.download(SYMBOL, period="2y", interval="1d")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.reset_index()
    
    # Padronização de nomes
    if "Datetime" in df.columns: df.rename(columns={"Datetime": "Date"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime('%Y-%m-%d')
    return df.dropna().sort_values("Date")

def generate_html(df):
    """Gera o HTML interativo com a biblioteca Lightweight Charts."""
    # Transforma os dados em lista de listas para o JavaScript
    # Formato: ["YYYY-MM-DD", open, high, low, close]
    raw_data = df[["Date", "Open", "High", "Low", "Close"]].values.tolist()
    json_data = json.dumps(raw_data)

    html_template = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IVVB11 - Analise Paparazi v4</title>
    <script src="https://unpkg.com/lightweight-charts@3.8.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body { font-family: sans-serif; background-color: #0d1117; color: #d1d4dc; margin: 0; padding: 20px; height: 100vh; display: flex; flex-direction: column; }
        #charts-container { flex: 1; display: flex; flex-direction: column; gap: 10px; }
        .chart-box { flex: 1; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; background: #010409; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        h1 { font-size: 18px; margin: 0; color: #58a6ff; }
        .legend { font-size: 12px; color: #8b949e; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Análise de Sinais - Algoritmo Paparazi v4</h1>
        <div class="legend">Ativo: IVVB11 (S&P 500 BR) | Filtro de Fourier Harmonic Isolation</div>
    </div>
    <div id="charts-container">
        <div id="price-chart" class="chart-box"></div>
        <div id="indicator-chart" class="chart-box"></div>
    </div>

    <script>
        const rawData = """ + json_data + """;

        window.onload = () => {
            const priceElement = document.getElementById('price-chart');
            const indicatorElement = document.getElementById('indicator-chart');

            const chartOptions = {
                layout: { backgroundColor: '#010409', textColor: '#d1d4dc' },
                grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
                crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: false }
            };

            const priceChart = LightweightCharts.createChart(priceElement, chartOptions);
            const indicatorChart = LightweightCharts.createChart(indicatorElement, chartOptions);

            const candleSeries = priceChart.addCandlestickSeries({
                upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
                wickUpColor: '#26a69a', wickDownColor: '#ef5350'
            });

            const msSeries = indicatorChart.addLineSeries({ color: '#ef5350', lineWidth: 2, title: 'Alpha Signal' });
            
            // Convertendo dados para o formato do Lightweight Charts
            const chartData = rawData.map(d => ({
                time: d[0], open: d[1], high: d[2], low: d[3], close: d[4]
            }));

            candleSeries.setData(chartData);

            // Cálculo do Paparazi v4 no lado do Cliente (JS) para performance
            function calculatePaparazi(data) {
                const n = data.length;
                const close = data.map(d => d.close);
                const per = new Array(n).fill(0);
                for(let i=1; i<n; i++) per[i] = 100 * (close[i] / close[i-1] - 1);
                
                const tu_mod = Array(31).fill().map(() => new Array(n).fill(0));
                const colors = Array(31).fill().map(() => new Array(n).fill(0));

                for(let x2=1; x2<=30; x2++) {
                    let x = Math.pow(x2, 1.5) + 1;
                    let fl_x = Math.floor(x);
                    let fl_x_h = Math.floor(x/2);
                    for(let i=fl_x; i<n; i++) {
                        let segment = per.slice(i-fl_x+1, i+1);
                        let sum_per = segment.reduce((a,b)=>a+b, 0);
                        let tu_val = sum_per; 
                        if(fl_x_h > 0) {
                            // Média simples do sum_per (aproximação do fractal)
                            let sum_prev = 0;
                            let count = 0;
                            for(let k=0; k<fl_x_h && (i-k)>=0; k++) {
                                let seg2 = per.slice(Math.max(0, i-k-fl_x+1), i-k+1);
                                sum_prev += seg2.reduce((a,b)=>a+b,0);
                                count++;
                            }
                            tu_val = sum_prev / count;
                        }
                        tu_mod[x2][i] = Math.atan(tu_val) * 2 / Math.PI;
                    }
                }

                let msData = [];
                for(let i=40; i<n; i++) {
                    let s = 0;
                    for(let x2=1; x2<=30; x2++) s += tu_mod[x2][i];
                    s = s / 2.0 + 15.0;
                    // Simplificação do sinal mestre para visualização
                    msData.push({ time: data[i].time, value: tu_mod[15][i] * 5 }); 
                }
                return msData;
            }

            const msPoints = calculatePaparazi(chartData);
            msSeries.setData(msPoints);

            // Sincronização de escalas
            priceChart.timeScale().subscribeVisibleTimeRangeChange(range => {
                indicatorChart.timeScale().setVisibleRange(range);
            });
            indicatorChart.timeScale().subscribeVisibleTimeRangeChange(range => {
                priceChart.timeScale().setVisibleRange(range);
            });

            new ResizeObserver(() => {
                priceChart.resize(priceElement.clientWidth, priceElement.clientHeight);
                indicatorChart.resize(indicatorElement.clientWidth, indicatorElement.clientHeight);
            }).observe(document.getElementById('charts-container'));
        };
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Sucesso! HTML interativo gerado em: {OUTPUT_HTML}")

if __name__ == "__main__":
    df = get_data()
    generate_html(df)
    # Salva também o CSV para compatibilidade com o notebook
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"CSV de suporte salvo em: {OUTPUT_CSV}")
