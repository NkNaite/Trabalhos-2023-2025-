import argparse
import sys
import os
import certifi

# Bootstrap dinâmico do SSL para PyInstaller
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

try:
    import yt_dlp
    import static_ffmpeg
    try:
        ffmpeg_path = static_ffmpeg.add_paths()
        # Algumas versões do static_ffmpeg retornam o path, outras não.
        # Mas o add_paths() geralmente injeta no PATH do sistema.
    except Exception:
        pass
except ImportError:
    pass

def parse_time_to_seconds(time_str):
    if not time_str: return None
    try:
        parts = list(map(int, str(time_str).split(":")))
        if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2: return parts[0] * 60 + parts[1]
        return float(parts[0])
    except (ValueError, IndexError):
        print(f"Aviso: Formato de tempo inválido: {time_str}")
        return 0.0

def download_clip(url, start_time, end_time=None, out_dir=None):
    if 'yt_dlp' not in sys.modules:
        raise ImportError("yt-dlp não está instalado.")

    print(f"Iniciando preparativos para o corte: {url}")
    print(f"Intervalo: {start_time} até {end_time if end_time else 'Fim do vídeo'}")

    start_s = parse_time_to_seconds(start_time)
    end_s = parse_time_to_seconds(end_time) if end_time else None
    
    outtmpl = '%(title)s_clip_%(id)s.%(ext)s'
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        outtmpl = os.path.join(out_dir, outtmpl)

    ydl_opts = {
        'outtmpl': outtmpl,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'force_keyframes_at_cuts': True,
        'quiet': False,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        'restrictfilenames': True, # Evita problemas com caracteres especiais no Windows
    }

    # Adiciona ranges de download
    if end_s is not None:
        print(f"Baixando fragmento: {start_s}s até {end_s}s...")
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(start_s, end_s)])
    else:
        print(f"Baixando fragmento: {start_s}s até o final...")
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(start_s, 999999)])

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("\n✅ Download da cena concluído com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro durante o download do corte: {e}")
        raise e # Re-levanta para que a GUI saiba que deu erro

def main():
    parser = argparse.ArgumentParser(description="Baixador Rapido de Cenas Específicas YouTube (Sem baixar arquivo completo)")
    parser.add_argument("--url", required=True, help="URL do vídeo do YouTube")
    parser.add_argument("--start", required=True, help="Tempo de início (Formato MM:SS ou HH:MM:SS)")
    parser.add_argument("--end", help="Tempo final (Formato MM:SS ou HH:MM:SS) - Opcional")
    parser.add_argument("--out_dir", help="Pasta de destino onde o vídeo será salvo", default=None)
    
    args = parser.parse_args()

    try:
        download_clip(args.url, args.start, args.end, args.out_dir)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()

