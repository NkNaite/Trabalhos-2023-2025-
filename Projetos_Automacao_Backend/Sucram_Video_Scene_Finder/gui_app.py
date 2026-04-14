import customtkinter as ctk
import threading
import sys
import os
import webbrowser
import json
import re
import requests
import subprocess
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="yt_dlp")

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

import cv2
from io import BytesIO
from PIL import Image
from main_uso import search_youtube_videos, analyze_transcript_with_gemini, create_html_report
import google.generativeai as genai
import dotenv

# Importa o módulo que acabamos de criar para baixar partes
try:
    from download_clip import download_clip
except ImportError:
    pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Video Scene Finder v2")
        self.geometry("1100x700")

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---------------- TOPO ---------------- #
        self.top_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.top_panel.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self.top_panel, text="Buscador Inteligente de Cenas", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, pady=(0, 20), sticky="w")

        self.input_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, sticky="ew")
        
        self.theme_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Tema (ex: cachorros na neve)", width=300, height=40)
        self.theme_entry.pack(side="left", padx=(0, 15))

        self.limit_label = ctk.CTkLabel(self.input_frame, text="Vídeos:")
        self.limit_label.pack(side="left", padx=(0, 5))

        self.limit_slider = ctk.CTkSlider(self.input_frame, from_=1, to=20, number_of_steps=19, width=120, command=self.update_limit_label)
        self.limit_slider.set(5)
        self.limit_slider.pack(side="left", padx=(0, 5))

        self.limit_value_label = ctk.CTkLabel(self.input_frame, text="5", font=ctk.CTkFont(weight="bold"))
        self.limit_value_label.pack(side="left", padx=(0, 20))

        self.btn_search = ctk.CTkButton(self.input_frame, text="▶️ Buscar Cenas", height=40, font=ctk.CTkFont(weight="bold"), command=self.start_process)
        self.btn_search.pack(side="left")

        self.output_folder = os.path.join(os.getcwd(), "resultados", "recortes")
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder, exist_ok=True)
            
        self.btn_folder = ctk.CTkButton(self.input_frame, text="📁 Destino", height=40, width=100, fg_color="#30363d", hover_color="#3c434a", command=self.select_folder)
        self.btn_folder.pack(side="left", padx=(10, 5))

        self.btn_api = ctk.CTkButton(self.input_frame, text="🔑 API Gemini", height=40, width=110, fg_color="#d29922", hover_color="#9e6a03", text_color="white", command=self.open_api_dialog)
        self.btn_api.pack(side="left", padx=(0, 5))

        # Settings
        self.settings_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.settings_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        # Configurações fixas (Modelo único original)
        self.max_workers = 2
        self.model_var = ctk.StringVar(value="gemini-1.5-flash")
        
        self.limit_simultaneous_label = ctk.CTkLabel(self.settings_frame, text="Velocidade de Processamento: Normal (2 concurrent)")
        self.limit_simultaneous_label.pack(side="left", padx=(0, 20))

        self.api_status_label = ctk.CTkLabel(self.settings_frame, text="✅ API OK", text_color="#2ea043", font=ctk.CTkFont(weight="bold"))
        self.api_status_label.pack(side="left", padx=(0, 10))

        current_api = os.environ.get("GEMINI_API_KEY", "")
        if not current_api or current_api == "sua_chave_aqui":
            self.api_status_label.configure(text="❌ API Não Configurada", text_color="#d73a49")

        # Loading
        self.progress_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, mode="determinate")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="0%")
        self.progress_label.pack(side="left")
        
        self.progress_frame.grid_remove() 

        # ---------------- MAIN ---------------- #
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Nenhum resultado", label_font=ctk.CTkFont(size=14, weight="bold"))
        self.results_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.results_frame.grid_columnconfigure(0, weight=1)

    def update_model_limit(self, choice):
        config = self.model_configs.get(choice, {"model": "gemini-2.5-flash", "limit": 2})
        self.max_workers = config["limit"]
        self.limit_simultaneous_label.configure(text=f"Max. Simultâneos (Velocidade): {self.max_workers}")

    def update_limit_label(self, value):
        self.limit_value_label.configure(text=str(int(value)))

    def select_folder(self):
        path = ctk.filedialog.askdirectory(title="Selecione a pasta para os downloads")
        if path:
            self.output_folder = path

    def open_api_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Configurar API Key do Gemini")
        dialog.geometry("500x250")
        dialog.transient(self)
        dialog.grab_set()

        lbl_title = ctk.CTkLabel(dialog, text="Insira sua API Key do Google Gemini:", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_title.pack(pady=(20, 10))

        entry_api = ctk.CTkEntry(dialog, placeholder_text="AIzaSy...", width=380, height=40)
        entry_api.pack(pady=10)
        # Preenche com a existente, se tiver
        current_api = os.environ.get("GEMINI_API_KEY", "")
        if current_api and current_api != "sua_chave_aqui":
            entry_api.insert(0, current_api)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)

        def save_api():
            new_key = entry_api.get().strip()
            if new_key:
                env_path = os.path.join(os.getcwd(), '.env')
                dotenv.set_key(env_path, 'GEMINI_API_KEY', new_key)
                os.environ['GEMINI_API_KEY'] = new_key
                genai.configure(api_key=new_key)
                self.api_status_label.configure(text="✅ API OK", text_color="#2ea043")
                dialog.destroy()

        btn_save = ctk.CTkButton(btn_frame, text="Salvar Chave", command=save_api, fg_color="#2ea043", hover_color="#238636")
        btn_save.pack(side="left", padx=10)

        btn_help = ctk.CTkButton(btn_frame, text="❔ O que é isso?", width=120, command=self.show_api_help, fg_color="#30363d", hover_color="#3c434a")
        btn_help.pack(side="left", padx=10)

    def show_api_help(self):
        help_dialog = ctk.CTkToplevel(self)
        help_dialog.title("Como conseguir sua API Key")
        help_dialog.geometry("550x350")
        help_dialog.transient(self)
        help_dialog.grab_set()
        
        texto = (
            "Para a Inteligência Artificial analisar os vídeos e recortar no tempo correto,\n"
            "ela precisa de acesso aos cérebros do Google Gemini. Isso é feito via 'API Key'.\n\n"
            "COMO CONSEGUIR A SUA (De graça):\n\n"
            "1. Acesse o site do Google AI Studio:\n"
            "   https://aistudio.google.com/app/apikey\n\n"
            "2. Faça login com sua conta do Google / Gmail.\n"
            "3. Clique no botão azul 'Create API key' (Criar chave de API).\n"
            "4. Uma vez criada, basta clicar para COPIAR o código gerado (começa com AIza...)\n"
            "5. Volte para este programa e cole o código na caixa anterior.\n\n"
            "Pronto! Você não paga nada e tem milhares de requisições de IA gratuitas por dia."
        )
        lbl = ctk.CTkLabel(help_dialog, text=texto, justify="left", wraplength=500, font=ctk.CTkFont(size=14))
        lbl.pack(padx=20, pady=20)
        
        btn_ok = ctk.CTkButton(help_dialog, text="Entendi", command=help_dialog.destroy)
        btn_ok.pack(pady=(0, 20))
            
    def set_progress(self, percent, text=""):
        self.after(0, self._set_progress_ui, percent, text)
        
    def _set_progress_ui(self, percent, text):
        if percent < 0:
            self.progress_frame.grid_remove()
            self.results_frame.configure(label_text=text)
        else:
            self.progress_frame.grid()
            self.progress_bar.set(percent / 100.0)
            self.progress_label.configure(text=f"{int(percent)}%")
            if text:
                self.results_frame.configure(label_text=text)

    def start_process(self):
        theme = self.theme_entry.get().strip()
        num_videos = int(self.limit_slider.get())
        if not theme: return
        
        current_api = os.environ.get("GEMINI_API_KEY", "")
        if not current_api or current_api == "sua_chave_aqui":
            self.set_progress(-1, "ERRO: Insira sua API Key do Gemini no botão 🔑 API Gemini!")
            return
            
        self.btn_search.configure(state="disabled", text="⏳ Processando...")
        self.set_progress(0, "Iniciando...")
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        threading.Thread(target=self.run_logic, args=(theme, num_videos)).start()

    def run_logic(self, theme, num_videos):
        import concurrent.futures
        try:
            self.set_progress(5, "Etapa 1: Buscando vídeos na rede...")
            videos = search_youtube_videos(theme, num_videos)
            
            if not videos:
                self.set_progress(-1, f"Nenhum vídeo para '{theme}'.")
                self.reset_button()
                return
                
            self.set_progress(15, f"Etapa 2: Validando {len(videos)} vídeos...")
            
            def process_video(i_vid):
                i, video = i_vid
                actual_model = "gemini-2.0-flash" # Atualizado para o modelo disponível na sua conta
                timestamps = analyze_transcript_with_gemini(video, theme, model_name=actual_model)
                video['timestamps'] = timestamps
                return video

            processed = []
            c = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(process_video, item): item for item in enumerate(videos, 1)}
                for future in concurrent.futures.as_completed(futures):
                    processed.append(future.result())
                    c += 1
                    self.set_progress(15 + (c / len(videos)) * 75, f"Analisando vídeos com IA ({c}/{len(videos)})...")

            self.set_progress(95, "Gerando HTML/Arquivos de Backup...")
            create_html_report(theme, processed)
            
            self.set_progress(100, f"✅ Processo Concluído!")
            self.after(0, lambda: self.render_results(processed))

        except Exception as e:
            self.set_progress(-1, f"Falha: {str(e)}")
        finally:
            self.after(2000, lambda: self.set_progress(-1, f"Resultados para: '{theme}'"))
            self.reset_button()

    def render_results(self, processed_videos):
        global_actions = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        global_actions.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        btn_dl_all_clips = ctk.CTkButton(global_actions, text="📥 Baixar Todos os Recortes", fg_color="#2ea043", hover_color="#238636", command=lambda: self.download_all_clips(processed_videos))
        btn_dl_all_clips.pack(side="left", padx=5)

        btn_dl_all_videos = ctk.CTkButton(global_actions, text="📥 Baixar Todos os Vídeos Completos", fg_color="#0366d6", hover_color="#005cc5", command=lambda: self.download_all_full_videos(processed_videos))
        btn_dl_all_videos.pack(side="left", padx=5)

        for idx, v in enumerate(processed_videos):
            row = ctk.CTkFrame(self.results_frame, fg_color="#1e1e1e", corner_radius=10)
            row.grid(row=idx+1, column=0, sticky="ew", padx=10, pady=10)
            row.grid_columnconfigure(1, weight=1)

            # Coluna 0: Thumbnail Info
            info_col = ctk.CTkFrame(row, fg_color="transparent")
            info_col.grid(row=0, column=0, sticky="nw", padx=15, pady=15)

            thumb_lbl = ctk.CTkLabel(info_col, text="", width=160, height=90, fg_color="gray20", corner_radius=6)
            thumb_lbl.pack(pady=(0, 10))
            threading.Thread(target=self.fetch_image, args=(v['thumbnail'], thumb_lbl)).start()

            lbl_chan = ctk.CTkLabel(info_col, text=f"📺 {v['channel'][:20]}\n⏳ {int(v['duration']//60)}m", text_color="gray70", justify="left")
            lbl_chan.pack(anchor="w")

            # Coluna 1: Conteudo
            content_col = ctk.CTkFrame(row, fg_color="transparent")
            content_col.grid(row=0, column=1, sticky="nsew", padx=(0,15), pady=15)

            title_row = ctk.CTkFrame(content_col, fg_color="transparent")
            title_row.pack(fill="x", pady=(0, 15))

            lbl_title = ctk.CTkLabel(title_row, text=v['title'], font=ctk.CTkFont(size=16, weight="bold"), anchor="w", justify="left", wraplength=550)
            lbl_title.pack(side="left", anchor="w")

            btn_dl_full = ctk.CTkButton(title_row, text="📥 Baixar Vídeo Completo", width=140, fg_color="#0366d6", hover_color="#005cc5")
            btn_dl_full.pack(side="right", padx=10)
            btn_dl_full.configure(command=lambda u=v['link'], b=btn_dl_full: self.do_download_full(u, b))

            time_lines = v.get('timestamps', '').split('\n')
            for line in time_lines:
                if not line.strip(): continue
                # Regex melhorada para suportar HH:MM:SS ou MM:SS
                match = re.search(r"(\d{1,2}:\d{1,2}(?::\d{1,2})?)(?:\s*-\s*(\d{1,2}:\d{1,2}(?::\d{1,2})?))?", line)
                if match:
                    st = match.group(1)
                    et = match.group(2)
                    
                    # Converte st para segundos para o player (aproximado)
                    s_parts = list(map(int, st.split(":")))
                    if len(s_parts) == 3: t_sec = s_parts[0]*3600 + s_parts[1]*60 + s_parts[2]
                    elif len(s_parts) == 2: t_sec = s_parts[0]*60 + s_parts[1]
                    else: t_sec = s_parts[0]

                    ts_row = ctk.CTkFrame(content_col, fg_color="gray12", corner_radius=5)
                    ts_row.pack(fill="x", pady=4, ipadx=5, ipady=5)

                    lbl_t = ctk.CTkLabel(ts_row, text=f"⌚ {line.strip()}", font=ctk.CTkFont(weight="bold", size=14), text_color="#ff7b72")
                    lbl_t.pack(side="left", padx=10)

                    btn_dl = ctk.CTkButton(ts_row, text="📥 Baixar Recorte", width=110, height=28,
                        fg_color="#2ea043", hover_color="#238636")
                    btn_dl.pack(side="left", padx=5)
                    btn_dl.configure(command=lambda u=v['link'], s=st, e=et, btn=btn_dl: self.do_download(u, s, e, btn))

                    btn_play = ctk.CTkButton(ts_row, text="▶️ Assistir Prévia", width=140, height=28,
                        command=lambda u=v['link'], t=t_sec, w=ts_row: self.start_native_player(u, t, w), fg_color="#d73a49", hover_color="#cb2431")
                    btn_play.pack(side="left", padx=5)

                    frames_container = ctk.CTkFrame(ts_row, fg_color="transparent")
                    frames_container.pack(side="left", padx=10)
                    
                    # Carrega dinamicamente a prévia assim que o resultado se formar sem precisar botão
                    self.load_three_scenes(v['link'], st, et, frames_container)

                else:
                    lbl_txt = ctk.CTkLabel(content_col, text=f"• {line}", text_color="gray80", anchor="w")
                    lbl_txt.pack(anchor="w", pady=2, padx=10)


    def fetch_image(self, url, lbl):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                im = Image.open(BytesIO(r.content))
                ck = ctk.CTkImage(light_image=im, dark_image=im, size=(160, 90))
                self.after(0, lambda: lbl.configure(image=ck))
        except: pass

    def do_download(self, url, start, end, btn):
        if btn: btn.configure(state="disabled", text="Baixando...")
        out_dir = getattr(self, "output_folder", os.path.join(os.getcwd(), "resultados", "recortes"))
        def run_dl():
            try:
                download_clip(url, start, end, out_dir=out_dir)
                if btn: self.after(0, lambda: btn.configure(text="✅ Concluído", fg_color="#2ea043"))
            except Exception as e:
                print(f"Erro a baixar: {e}")
                # Log do erro para depuração
                with open("error_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"CLIP DL ERROR: {str(e)} | URL: {url} | range: {start}-{end}\n")
                if btn: self.after(0, lambda: btn.configure(text="❌ Erro", fg_color="#d73a49"))
        threading.Thread(target=run_dl).start()

    def do_download_full(self, url, btn):
        if btn: btn.configure(state="disabled", text="Baixando...")
        out_dir = getattr(self, "output_folder", os.path.join(os.getcwd(), "resultados", "recortes"))
        def run_dl():
            try:
                import yt_dlp
                ydl_opts = {
                    'outtmpl': os.path.join(out_dir, '%(title)s_completo_%(id)s.%(ext)s'),
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'quiet': False,
                    'nocheckcertificate': True,
                    'restrictfilenames': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                if btn: self.after(0, lambda: btn.configure(text="✅ Concluído", fg_color="#2ea043"))
            except Exception as e:
                print(f"Erro a baixar completo: {e}")
                # Log do erro para depuração
                with open("error_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"FULL DL ERROR: {str(e)}\n")
                if btn: self.after(0, lambda: btn.configure(text="❌ Erro", fg_color="#d73a49"))
        threading.Thread(target=run_dl).start()

    def download_all_clips(self, processed_videos):
        for v in processed_videos:
            url = v['link']
            time_lines = v.get('timestamps', '').split('\n')
            for line in time_lines:
                if not line.strip(): continue
                match = re.search(r"(\d{1,2}:\d{2})(?:\s*-\s*(\d{1,2}:\d{2}))?", line)
                if match:
                    st = match.group(1)
                    et = match.group(2)
                    self.do_download(url, st, et, None)

    def download_all_full_videos(self, processed_videos):
        for v in processed_videos:
            self.do_download_full(v['link'], None)

    def start_native_player(self, url, start_sec, container):
        # Destrói player anterior se existir ali
        for w in container.winfo_children():
            if getattr(w, "is_player", False):
                w.destroy()
        
        player_lbl = ctk.CTkLabel(container, text="Carregando Vídeo...", fg_color="black", width=250, height=140)
        player_lbl.pack(side="top", pady=10)
        player_lbl.is_player = True # Marca o widget

        def video_loop():
            try:
                import yt_dlp
                opts = {'format': 'worst[ext=mp4]', 'quiet': True, 'nocheckcertificate': True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    stream_url = info['url']
                
                cap = cv2.VideoCapture(stream_url)
                cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
                
                def render_frame():
                    if not player_lbl.winfo_exists():
                        cap.release()
                        return
                    
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 140))
                        # Use self.after para atualizar UI a partir da thread
                        self.after(0, lambda: player_lbl.configure(image=ctk_img, text=""))
                        self.after(33, render_frame) # 30 fps
                    else:
                        self.after(0, lambda: player_lbl.configure(text="Fim do Vídeo."))
                        cap.release()
                        
                render_frame()
            except Exception as e:
                self.after(0, lambda: player_lbl.configure(text=f"Erro no player: {str(e)[:20]}"))
        
        threading.Thread(target=video_loop).start()

    def load_three_scenes(self, url, st, et, container):
        loading = ctk.CTkLabel(container, text="⏳ Gerando cenas via ffmpeg...", text_color="gray50")
        loading.pack(side="left")

        def run():
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL({'quiet': True, 'format': 'worst[ext=mp4]', 'nocheckcertificate': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    s_url = info['url']
                
                ms = re.search(r"(\d+):(\d+)", st)
                ss = int(ms.group(1))*60 + int(ms.group(2))
                es = ss + 15
                if et:
                    me = re.search(r"(\d+):(\d+)", et)
                    if me: es = int(me.group(1))*60 + int(me.group(2))
                
                dur = max(es - ss, 3)
                t1, t2, t3 = ss, ss + dur//2, es

                images = []
                cap = cv2.VideoCapture(s_url)
                
                for t in [t1, t2, t3]:
                    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame)
                        images.append(ctk.CTkImage(light_image=img, dark_image=img, size=(100, 56)))
                cap.release()
                
                self.after(0, lambda: self._show_scenes(container, loading, images))
            except Exception as e:
                print("Erro captura cenas nativa:", e)
                self.after(0, lambda: loading.configure(text="Erro nas imagens."))
        threading.Thread(target=run).start()

    def _show_scenes(self, container, loading, images):
        loading.destroy()
        for img in images:
            l = ctk.CTkLabel(container, image=img, text="")
            l.pack(side="left", padx=3)

    def reset_button(self):
        self.after(0, lambda: self.btn_search.configure(state="normal", text="▶️ Buscar Cenas"))

if __name__ == "__main__":
    app = App()
    app.mainloop()
