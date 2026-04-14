import os
import argparse
import yt_dlp
import re

def clean_filename(title):
    # Remove caracteres inválidos para nome de arquivo
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    return safe_title[:50] # Limita tamanho

def download_video_high_quality(video_url):
    print(f"Baixando vídeo em alta qualidade da URL: {video_url}")
    
    # Primeiro, extraímos a info para pegar o título limpo
    ydl_opts_info = {
        'quiet': True,
        'skip_download': True,
    }
    
    video_title = "video_baixado"
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            video_title = clean_filename(info_dict.get('title', 'video_baixado'))
    except Exception as e:
        print(f"Aviso: Não foi possível pegar o título. Usando nome padrão. ({e})")
        
    output_path = f"{video_title}.mp4"
    
    # Agora fazemos o download real em alta qualidade
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            return output_path
    except Exception as e:
        print(f"Erro ao baixar vídeo: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Download de Vídeos Alta Qualidade (Local/GitHub Artifact)")
    parser.add_argument("indices", type=str, help="Números dos vídeos para baixar (ex: 1, 2, 5)")
    
    args = parser.parse_args()
    indices_raw = args.indices
    
    # Processa os índices inseridos (ex: "1, 2, 5" vira ['1', '2', '5'])
    chosen_indices = [idx.strip() for idx in indices_raw.split(",") if idx.strip()]
    
    if not os.path.exists("resultados/urls.json"):
        print("❌ Erro: O arquivo 'resultados/urls.json' não foi encontrado.")
        print("Você deve primeiro rodar a Fase 1 (Busca) ou garantir que os resultados foram baixados.")
        return

    import json
    with open("resultados/urls.json", "r", encoding="utf-8") as f:
        urls_map = json.load(f)
        
    for index in chosen_indices:
        if index not in urls_map:
            print(f"⚠️ Aviso: O vídeo de número {index} não foi encontrado na lista de busca anterior. Pulando...")
            continue
            
        video_url = urls_map[index]
        print(f"\n--- Iniciando Download do Vídeo {index} ---")
        local_path = download_video_high_quality(video_url)
        
        if local_path and os.path.exists(local_path):
            print(f"✅ Vídeo {index} concluído com sucesso! (Salvo como: {local_path})")
        else:
            print(f"❌ Falha ao baixar o vídeo {index}.")
            
    print("\nTodos os downloads possíveis foram finalizados!")
    print("Se estiver rodando no GitHub Actions, os arquivos estarão disponíveis na aba 'Artifacts'.")
        
if __name__ == "__main__":
    main()
