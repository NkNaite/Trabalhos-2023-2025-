import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from youtubesearchpython import VideosSearch
import yt_dlp
import cv2
import re
import argparse
import json

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configura a chave da API do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "sua_chave_aqui":
    print("ERRO: Chave API do Gemini não encontrada ou não configurada.")
    print("Por favor, adicione sua chave no arquivo .env")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)


def optimize_search_term(theme):
    """
    Usa o Gemini (Texto) para gerar termos de busca otimizados para o YouTube.
    """
    print(f"\n[1/5] Otimizando termo de busca '{theme}' com IA...")
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    O usuário quer achar vídeos no Youtube com cenas de [{theme}]. 
    Escreva a melhor sugestão de termo de busca (apenas 1 frase curta) que dará os melhores resultados do YouTube para isso.
    Retorne apenas o termo de busca, sem aspas e sem explicações.
    """
    try:
        response = model.generate_content(prompt)
        optimized_term = response.text.strip()
        print(f"Termo otimizado sugerido: '{optimized_term}'")
        return optimized_term
    except Exception as e:
        print(f"Erro ao otimizar termo: {e}")
        return theme


# Configuração de limites
MAX_VIDEO_DURATION = 600 # 10 minutos (em segundos)

def search_youtube_videos(query, max_results):
    """
    Busca vídeos no YouTube usando yt-dlp e filtra por duração para evitar vídeos longos.
    """
    # Buscamos muito a mais para ter margem de manobra (ex: se todos do topo forem lives)
    search_limit = max(max_results * 5, 20)
    print(f"\n[2/5] Buscando vídeos no YouTube para: '{query}' (Limite: {max_results} vídeos curtos/médios)...")
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'force_generic_extractor': False,
        'extractor_args': {'youtube': {'player_client': ['web']}}
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{search_limit}:{query}"
            result = ydl.extract_info(search_query, download=False)
            
            if 'entries' not in result:
                return []
                
            video_data = []
            for entry in result['entries']:
                # Pula transmissões ao vivo explícitas
                if entry.get('is_live') or entry.get('live_status') == 'is_live':
                    print(f"PULANDO: Vídeo '{entry.get('title')[:30]}...' é uma transmissão ao vivo.")
                    continue
                
                # Verifica a duração (se disponível)
                duration = entry.get('duration')
                
                if duration is None or duration == 0:
                    print(f"PULANDO: Vídeo '{entry.get('title')[:30]}...' não tem duração definida (possível live).")
                    continue
                
                if duration > MAX_VIDEO_DURATION:
                    print(f"PULANDO: Vídeo '{entry.get('title')[:30]}...' é muito longo ({duration//60} min).")
                    continue
                
                video_data.append({
                    'title': entry.get('title'),
                    'link': f"https://www.youtube.com/watch?v={entry.get('id')}",
                    'id': entry.get('id'),
                    'duration': duration
                })
                
                # Se já atingimos a quantidade desejada, paramos
                if len(video_data) >= max_results:
                    break
                    
            print(f"Encontrados {len(video_data)} vídeos adequados.")
            return video_data
    except Exception as e:
        print(f"Erro ao buscar no YouTube: {e}")
        return []
        print(f"Erro ao buscar no YouTube: {e}")
        return []

def download_video(video_url, output_path):
    """
    Baixa o vídeo temporariamente usando yt-dlp em baixa resolução 
    (para o Gemini conseguir processar rápido).
    """
    print(f"Baixando vídeo temporariamente: {video_url}")
    
    ydl_opts = {
        'format': 'b[ext=mp4]', # 'b' significa best single stream (evita FFmpeg e merge) 
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['web']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return True
    except Exception as e:
        print(f"Erro ao baixar vídeo: {e}")
        return False

def analyze_video_with_gemini(video_path, theme):
    """
    Faz upload do vídeo pro Gemini e extrai a minutagem das cenas.
    """
    print(f"Enviando vídeo para a API do Google Gemini...")
    try:
        video_file = genai.upload_file(path=video_path)
        
        # Espera o arquivo ser processado pela API
        print("Aguardando processamento do vídeo no servidor...")
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            # Atualiza o status do arquivo
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            print("Falha ao processar o vídeo no servidor do Google.")
            return "Falha no processamento."

        print("Analisando conteúdo com a IA...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Observe este vídeo com atenção. Localize os exatos minutos e segundos onde mostram a cena [{theme}]. 
        Se a cena aparecer, me dê o formato de saída exato para cada ocorrência: MM:SS - MM:SS.
        Se a cena não aparecer em nenhum momento, responda apenas: Nenhuma cena encontrada.
        Não forneça explicações adicionais, apenas as minutagens se houver.
        """
        response = model.generate_content([prompt, video_file], request_options={"timeout": 600})
        
        # Deletar arquivo dos servidores após uso
        genai.delete_file(video_file.name)
        
        return response.text.strip()
    except Exception as e:
        print(f"Erro na análise do Gemini: {e}")
        return "Erro na análise."

def extract_median_frames(video_path, timestamps_text, video_id):
    """
    Analisa o texto do Gemini, extrai até 5 minutagens, calcula o tempo mediano de cada uma e gera imagens (prints).
    """
    print(f"Extraindo prints (máximo de 5) baseados na análise...")
    
    # Padrão flexível para suportar MM:SS - MM:SS ou M:SS - M:SS
    pattern = r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})"
    matches = re.findall(pattern, timestamps_text)
    
    if not matches:
        print("Nenhuma minutagem clara encontrada para gerar prints.")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Erro ao tentar ler o vídeo para tirar prints.")
        return
        
    prints_count = 0
    
    # Pega no máximo os 5 primeiros matches
    for match in matches[:5]:
        start_min, start_sec, end_min, end_sec = map(int, match)
        
        start_total_sec = (start_min * 60) + start_sec
        end_total_sec = (end_min * 60) + end_sec
        
        # Calcula o meio exato da cena
        median_sec = (start_total_sec + end_total_sec) / 2.0
        
        # Posiciona o leitor OpenCV em milissegundos
        cap.set(cv2.CAP_PROP_POS_MSEC, median_sec * 1000)
        ret, frame = cap.read()
        
        if ret:
            safe_id = "".join(x for x in video_id if x.isalnum())
            filename = f"resultados/print_{safe_id}_{int(median_sec)}s.jpg"
            cv2.imwrite(filename, frame)
            prints_count += 1
            
    cap.release()
    print(f"-> {prints_count} prints gerados e salvos na pasta 'resultados/'.")

def main():
    parser = argparse.ArgumentParser(description="Buscador de Cenas de Vídeo IA")
    parser.add_argument("--theme", type=str, required=True, help="Tema das cenas (ex: casas no marrocos)")
    parser.add_argument("--limit", type=int, default=30, help="Quantidade de vídeos para buscar")
    args = parser.parse_args()

    theme = args.theme
    num_videos = args.limit

    print("=" * 50)
    print(" Buscador de Cenas IA - Fase 1 (Busca)")
    print("=" * 50)
    print(f"Tema escolhido: {theme}")
    print(f"Buscando até {num_videos} vídeos.\n")
    
    # Criar pasta para resultados
    if not os.path.exists("resultados"):
        os.makedirs("resultados")

    # 1. Otimizar a busca
    optimized_query = optimize_search_term(theme)
    
    # 2. Buscar no YouTube
    videos = search_youtube_videos(optimized_query, num_videos)
    if not videos:
        print("Nenhum vídeo encontrado.")
        return
        
    # 3. Preparar arquivo de saída
    output_filename = "resultados/relatorio_cenas.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"Relatório de Cenas - Tema: {theme}\n")
        f.write(f"Busca Otimizada: {optimized_query}\n")
        f.write("=" * 50 + "\n\n")

    video_urls_map = {}
        
    # 4. Processar cada vídeo
    print(f"\n[3/5] Iniciando processamento de {len(videos)} vídeos...")
    for i, video in enumerate(videos, 1):
        print(f"\n--- Processando Vídeo {i}/{len(videos)} ---")
        print(f"Título: {video['title']}")
        print(f"Link: {video['link']}")
        
        temp_video_path = f"temp_video_{video['id']}.mp4"
        
        # Baixar
        if download_video(video['link'], temp_video_path):
            # Analisar
            timestamps = analyze_video_with_gemini(temp_video_path, theme)
            print(f"Resultado:\n{timestamps}")
            
            # Salvar no mapa de urls
            video_urls_map[str(i)] = video['link']

            # Salvar no arquivo
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"🎥 VÍDEO {i}\n")
                f.write(f"Título: {video['title']}\n")
                f.write(f"Link: {video['link']}\n")
                f.write(f"Cenas ({theme}):\n{timestamps}\n")
                f.write("-" * 50 + "\n\n")
                
            # Disparar função para gerar os prints com base nas minutagens encontradas
            extract_median_frames(temp_video_path, timestamps, video['id'])
                
            # Limpar arquivo local
            try:
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            except Exception as e:
                print(f"Aviso: Não foi possível deletar arquivo temporário {temp_video_path}")
        else:
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"🎥 VÍDEO {i}\n")
                f.write(f"Título: {video['title']}\n")
                f.write(f"Link: {video['link']}\n")
                f.write(f"Cenas ({theme}): Falha no download do vídeo.\n")
                f.write("-" * 50 + "\n\n")

    # Salvar o dicionario JSON para uso da Fase 2
    with open("resultados/urls.json", "w", encoding="utf-8") as fjson:
        json.dump(video_urls_map, fjson, indent=4)

    print(f"\n[5/5] Processo finalizado! O relatório foi salvo em '{output_filename}'")


if __name__ == "__main__":
    main()
