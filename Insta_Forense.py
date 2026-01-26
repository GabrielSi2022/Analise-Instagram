import sqlite3
import datetime
import json
import os
import sys
import re
import tkinter as tk
import hashlib
import webbrowser
from tkinter import filedialog, messagebox, ttk
import bisect
import base64
from itertools import groupby
import warnings

# --- TENTATIVA DE IMPORTAR O WHISPER (IA) ---
try:
    import whisper

    TEM_WHISPER = True
except ImportError:
    TEM_WHISPER = False
    print("AVISO: Biblioteca 'openai-whisper' não instalada.")


# --- TRUQUE PARA O FFMPEG RODAR DENTRO DO EXE (PORTABLE) ---
def configurar_ffmpeg_path():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
        os.environ["PATH"] += os.pathsep + base_path


configurar_ffmpeg_path()


# --- CLASSE PARA LIMPAR O VISUAL DO DOWNLOAD ---
class RedirecionadorLog:
    def __init__(self, widget):
        self.widget = widget
        self.ultima_foi_progresso = False

    def write(self, texto):
        if not texto:
            return
        e_progresso = "%" in texto or "\r" in texto
        if e_progresso and self.ultima_foi_progresso:
            self.widget.delete("end-2l", "end-1l")
        texto_limpo = texto.replace("\r", "").rstrip()
        if texto_limpo:
            self.widget.insert(tk.END, texto_limpo + "\n")
            self.widget.see(tk.END)
            self.widget.update()
            self.ultima_foi_progresso = e_progresso

    def flush(self):
        pass


# --- CONFIGURAÇÕES GERAIS ---
MARGEM_ERRO_MS = 60000
TAMANHO_MINIMO_KB = 1
ANO_MINIMO = 2015
ANO_MAXIMO = 2029
ARQUIVO_CONFIG = "config_forense.json"

# --- TEXTO TÉCNICO ---
TEXTO_INTRODUCAO_TECNICA = """
<div style="background-color: #f8f9fa; padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; font-size: 13px; color: #333; text-align: justify;">
    <h3 style="color: #b71c1c; margin-top: 0;">Introdução Técnica & Integridade dos Dados</h3>
    <p>O presente relatório foi gerado automaticamente pelo software de análise forense desenvolvido para auxílio na materialização de evidências digitais.</p>
    <p>Este documento contém os metadados do arquivo de banco de dados analisado, além da aplicação das funções hashes para garantia de integridade.</p>
    <p><strong>Conceito Forense:</strong> O que torna esse tipo de função essencial para a verificação de integridade é que uma simples alteração de um bit no arquivo original gerará um hash completamente diferente (ELEUTÉRIO e MACHADO, 2011).</p>
    <p><strong>Validade Jurídica:</strong> O uso deste método é reconhecido pelo ordenamento jurídico brasileiro (STJ, AgRg no HC 828054/RN, 23/04/2024), garantindo a "mesmidade" dos elementos digitais.</p>
</div>
"""


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


PASTA_LOGOS = resource_path("logos")
ARQUIVO_MANUAL = resource_path("manual.pdf")


# --- UTILITÁRIOS ---
def carregar_configuracoes():
    padrao = {
        "instituicao": "Delegacia de Polícia Civil",
        "logo_path": "",
        "tipo_envolvido": "Investigado",
    }
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                conf = json.load(f)
                for k, v in padrao.items():
                    if k not in conf:
                        conf[k] = v
                return conf
        except:
            return padrao
    return padrao


def salvar_configuracoes(instituicao, logo_path, tipo_envolvido):
    dados = {
        "instituicao": instituicao,
        "logo_path": logo_path,
        "tipo_envolvido": tipo_envolvido,
    }
    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
    except:
        pass


def imagem_para_base64(caminho_imagem):
    if not caminho_imagem or not os.path.exists(caminho_imagem):
        return ""
    try:
        with open(caminho_imagem, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            ext = os.path.splitext(caminho_imagem)[1].lower().replace(".", "")
            if ext == "jpg":
                ext = "jpeg"
            return f"data:image/{ext};base64,{encoded_string}"
    except:
        return ""


def listar_logos_padrao():
    logos = []
    if os.path.exists(PASTA_LOGOS):
        try:
            for f in os.listdir(PASTA_LOGOS):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    logos.append(f)
        except:
            pass
    logos.sort()
    return logos


def calcular_hashes_arquivo(caminho_arquivo):
    if not caminho_arquivo or not os.path.exists(caminho_arquivo):
        return None
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    try:
        with open(caminho_arquivo, "rb") as f:
            while chunk := f.read(8192):
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
        tamanho = os.path.getsize(caminho_arquivo)
        modificacao = datetime.datetime.fromtimestamp(
            os.path.getmtime(caminho_arquivo)
        ).strftime("%d/%m/%Y %H:%M:%S")
        return {
            "nome": os.path.basename(caminho_arquivo),
            "caminho": caminho_arquivo,
            "tamanho": f"{tamanho:,} bytes".replace(",", "."),
            "modificacao": modificacao,
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "sha256": sha256.hexdigest(),
        }
    except:
        return None


def abrir_manual_pdf():
    if os.path.exists(ARQUIVO_MANUAL):
        try:
            webbrowser.open(ARQUIVO_MANUAL)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o manual: {e}")
    else:
        messagebox.showwarning(
            "Aviso", "O arquivo 'manual.pdf' não foi encontrado na pasta do sistema."
        )


# --- ENGENHARIA DE DADOS ---


def obter_timestamp_sistema(caminho):
    try:
        return int(os.path.getmtime(caminho) * 1000)
    except:
        return 0


def analisar_arquivo_midia(caminho):
    nome_arquivo = os.path.basename(caminho)
    ts_sistema = obter_timestamp_sistema(caminho)
    match_audio = re.search(r"audio_(\d+)_", nome_arquivo)
    if match_audio:
        return int(match_audio.group(1)), 0, "voice"
    matches = re.findall(r"(1[2-9]\d{12})", nome_arquivo)
    if matches:
        return int(matches[-1]), 0, "id_generico"
    match_data = re.search(
        r"(20[1-2][0-9])(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])", nome_arquivo
    )
    if match_data:
        try:
            dt = datetime.datetime(
                int(match_data.group(1)),
                int(match_data.group(2)),
                int(match_data.group(3)),
                12,
                0,
            )
            return int(dt.timestamp() * 1000), 0, "data_nome"
        except:
            pass
    if ts_sistema > 0:
        try:
            ano_sys = datetime.datetime.fromtimestamp(ts_sistema / 1000.0).year
            if ANO_MINIMO <= ano_sys <= ANO_MAXIMO:
                return None, ts_sistema, "sistema"
        except:
            pass
    return None, None, False


def indexar_tudo(pasta_backup, log_widget):
    arquivos_voice_message = []
    index_ids_geral = []
    index_sistema = []
    lista_galeria = []
    arquivos_vistos = set()
    count_total = 0
    for root, dirs, files in os.walk(pasta_backup):
        for file in files:
            if file.lower().endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".mp4",
                    ".m4a",
                    ".opus",
                    ".wav",
                    ".mp3",
                    ".webp",
                    ".3gp",
                    ".amr",
                    ".ogg",
                )
            ):
                caminho = os.path.join(root, file).replace("\\", "/")
                try:
                    tamanho = os.path.getsize(caminho)
                except:
                    continue
                if tamanho < (TAMANHO_MINIMO_KB * 1024):
                    continue
                ts_nome, ts_sistema, tipo_match = analisar_arquivo_midia(caminho)
                if tipo_match:
                    ts_exibicao = ts_nome if ts_nome else ts_sistema
                    chave_unica = (tamanho, ts_exibicao)
                    if chave_unica in arquivos_vistos:
                        continue
                    arquivos_vistos.add(chave_unica)
                    count_total += 1
                    if tipo_match == "voice":
                        arquivos_voice_message.append(
                            {"ts": ts_nome, "caminho": caminho}
                        )
                    elif tipo_match == "id_generico":
                        index_ids_geral.append((ts_nome, caminho))
                    elif tipo_match == "sistema":
                        index_sistema.append((ts_sistema, caminho))
                    elif tipo_match == "data_nome":
                        index_ids_geral.append((ts_nome, caminho))
                    lista_galeria.append(
                        {"ts": ts_exibicao, "caminho": caminho, "nome": file}
                    )
    arquivos_voice_message.sort(key=lambda x: x["ts"])
    index_ids_geral.sort(key=lambda x: x[0])
    index_sistema.sort(key=lambda x: x[0])
    log_widget.insert(
        tk.END,
        f"Total Indexado: {count_total} (Voice Messages: {len(arquivos_voice_message)})\n",
    )
    return arquivos_voice_message, index_ids_geral, index_sistema, lista_galeria


def realizar_match_heuristico(mensagens_db, arquivos_voice):
    mapa_matches = {}
    # Cria uma cópia para poder remover os já usados
    arquivos_disponiveis = arquivos_voice.copy()

    msgs_candidatas = []

    # LISTA AMPLIADA DE TIPOS QUE PODEM CONTER ÁUDIO
    tipos_aceitos = [
        "audio",
        "voice_media",
        "clip",
        "raven_media",
        "visual_media",
        "ephemeral",
    ]

    for m in mensagens_db:
        mtype = m[4]
        msg_text = str(m[3]) if m[3] else ""

        # Verifica se é um tipo de áudio OU se é um link/texto que parece áudio
        eh_candidato = (
            (mtype in tipos_aceitos)
            or (mtype == "link" and "audio" in msg_text)
            or ("audio" in msg_text.lower())
        )

        if eh_candidato:
            ts_msg = int(m[1])
            # Corrige timestamps em microssegundos para milissegundos
            if ts_msg > 10000000000000:
                ts_msg = int(ts_msg / 1000)
            msgs_candidatas.append(
                {"ts": ts_msg, "id_msg": m[0]}
            )  # Salvando ID para debug se precisar

    # AUMENTANDO A TOLERÂNCIA PARA 24 HORAS (para pegar casos de download tardio)
    TOLERANCIA_MAXIMA = 86400000  # 24 horas em milissegundos

    # Ordena as mensagens por data para otimizar
    msgs_candidatas.sort(key=lambda x: x["ts"])

    for msg in msgs_candidatas:
        melhor_arq = None
        menor_diff = float("inf")
        indice_remover = -1

        for i, arq in enumerate(arquivos_disponiveis):
            diff = abs(msg["ts"] - arq["ts"])

            # Se a diferença for aceitável
            if diff < TOLERANCIA_MAXIMA:
                # Se achamos um match QUASE PERFEITO (menos de 5 segundos), paramos de procurar
                if diff < 5000:
                    melhor_arq = arq["caminho"]
                    indice_remover = i
                    break  # Sai do loop interno e já vincula

                # Senão, continuamos procurando o "menos pior"
                if diff < menor_diff:
                    menor_diff = diff
                    melhor_arq = arq["caminho"]
                    indice_remover = i

        if melhor_arq:
            mapa_matches[msg["ts"]] = melhor_arq
            # Remove o arquivo da lista para não vincular ele a duas mensagens
            if indice_remover != -1:
                arquivos_disponiveis.pop(indice_remover)

    return mapa_matches


def buscar_midia_comum(ts_msg, lista_geral, lista_sistema):
    if not ts_msg:
        return None
    t_raw = int(ts_msg)
    t_ms = int(t_raw / 1000) if t_raw > 10000000000000 else t_raw

    def buscar(lista, alvo, margem):
        if not lista:
            return None
        chaves = [x[0] for x in lista]
        pos = bisect.bisect_left(chaves, alvo)
        candidatos = []
        indices = [pos - 1, pos, pos + 1]
        for i in indices:
            if 0 <= i < len(lista):
                ts, path = lista[i]
                if abs(ts - alvo) <= margem:
                    candidatos.append((abs(ts - alvo), path))
        if candidatos:
            candidatos.sort(key=lambda x: x[0])
            return candidatos[0][1]
        return None

    res = buscar(lista_geral, t_ms, 1000)
    if res:
        return res
    return buscar(lista_sistema, t_ms, 300000)


# --- RELATÓRIO HTML ---
class RelatorioHTML:
    def __init__(self):
        self.html_parts = []
        self.css = """<style>
        body{font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#e9ebee;margin:0;padding:20px;color:#1c1e21}
        .container{max-width:950px;margin:0 auto;background:white;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.15);overflow:hidden}
        .header{background:#222;padding:30px;border-bottom:6px solid #b71c1c;color:white;text-align:center}
        .pcmg-logo{max-height:120px;max-width:100%;margin-bottom:15px;display:block;margin-left:auto;margin-right:auto;object-fit:contain}
        .header h1{margin:0;font-size:24px;text-transform:uppercase;letter-spacing:1.2px;font-weight:800}
        .header h2{margin:8px 0 0;font-size:15px;font-weight:400;color:#ddd}
        .meta-info{margin-top:20px;font-size:13px;color:#ccc;line-height:1.6;border:1px solid #444;display:inline-block;padding:10px 20px;border-radius:4px;background:#333}
        .hash-table{width:100%;border-collapse:collapse;margin-top:10px;font-family:'Consolas',monospace;font-size:11px}
        .hash-table td{border:1px solid #ddd;padding:8px}
        .hash-table tr:nth-child(even){background-color:#f2f2f2}
        .hash-table th{padding:8px;background-color:#333;color:white;text-align:left}
        .search-bar{position:sticky;top:0;background:#fff;padding:15px;z-index:100;border-bottom:1px solid #ddd;box-shadow:0 2px 5px rgba(0,0,0,0.05)}
        .search-input{width:100%;padding:10px;font-size:14px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box}
        .chat-box{padding:30px;display:flex;flex-direction:column;gap:15px;background:#fff}
        .chat-container{margin-bottom:30px;background:#fff;border:1px solid #eee;border-radius:8px;overflow:hidden}
        .chat-container-header{background-color:#f8f9fa;padding:15px;text-align:center;font-weight:bold;border-bottom:2px solid #e9ebee;color:#555}
        .chat-container-body{padding:15px;display:flex;flex-direction:column;gap:10px}
        .msg{max-width:80%;padding:12px 18px;border-radius:18px;font-size:14px;position:relative;line-height:1.5;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
        .sent .msg{background-color:#0084ff;color:white;border-bottom-right-radius:2px;align-self:flex-end}
        .received .msg{background-color:#f0f2f5;color:#050505;border-bottom-left-radius:2px;border:1px solid #ddd;align-self:flex-start}
        .msg-wrapper{display:flex;flex-direction:column;margin-bottom:5px}
        .msg-wrapper.sent{align-items:flex-end}
        .msg-wrapper.received{align-items:flex-start}
        .sender-name{font-size:11px;color:#666;margin-left:12px;margin-bottom:2px;font-weight:700;margin-top:5px}
        .meta{font-size:10px;margin-top:5px;opacity:0.7;text-align:right}
        .stories-section{padding:30px;border-top:8px solid #833AB4;background:#fdfdfd}
        .section-title{color:#833AB4;font-size:20px;border-bottom:1px solid #eee;padding-bottom:10px;margin-bottom:20px}
        .story-card{background:#fff;border:1px solid #e0e0e0;padding:15px;margin-bottom:15px;border-radius:8px;display:flex;gap:20px;align-items:center;transition:transform 0.2s}
        .story-card:hover{transform:translateY(-2px);box-shadow:0 4px 8px rgba(0,0,0,0.1)}
        .story-preview{width:160px;display:flex;flex-direction:column;justify-content:center;align-items:center;background:#000;border-radius:6px;overflow:hidden;min-height:100px;padding:5px}
        .story-info{flex:1}
        img,video{max-width:100%;max-height:300px;display:block;border-radius:8px}
        audio{width:250px;height:40px}
        .btn-open{display:inline-block;margin-top:8px;padding:6px 12px;background-color:#333;color:#fff!important;text-decoration:none;font-size:11px;border-radius:4px;font-weight:bold;text-align:center;border:1px solid #000;cursor:pointer}
        .btn-open:hover{background-color:#555}
        .audio-container{margin-top:8px;background:rgba(255,255,255,0.2);padding:5px;border-radius:10px;display:inline-block}
        .received .audio-container{background:rgba(0,0,0,0.05)}
        .transcription {
            font-size: 13px; color: #222; font-style: italic; font-weight: 500;
            margin-top: 10px; background-color: rgba(255, 255, 255, 0.6);
            padding: 8px; border-radius: 4px; border-left: 4px solid #b71c1c;
        }
        .sent .transcription { color: #fff; background-color: rgba(0,0,0,0.2); border-left-color: #fff; }
        </style>"""

    def iniciar(
        self,
        nome_dono,
        id_dono,
        arquivo_db,
        nome_instituicao,
        logo_src,
        tipo_envolvido,
        dados_hash=None,
    ):
        img_tag = f'<img src="{logo_src}" class="pcmg-logo">' if logo_src else ""
        html_hash = ""
        if dados_hash:
            html_hash = f"""<div style="margin-top:10px;"><table class="hash-table"><tr><th colspan="2">DADOS TÉCNICOS DA FONTE (ARQUIVO ANALISADO)</th></tr><tr><td><strong>Nome do Arquivo:</strong></td><td>{dados_hash['nome']}</td></tr><tr><td><strong>Caminho Original:</strong></td><td>{dados_hash['caminho']}</td></tr><tr><td><strong>Tamanho:</strong></td><td>{dados_hash['tamanho']}</td></tr><tr><td><strong>Data Modificação:</strong></td><td>{dados_hash['modificacao']}</td></tr><tr><td><strong>MD5:</strong></td><td>{dados_hash['md5']}</td></tr><tr><td><strong>SHA-1:</strong></td><td>{dados_hash['sha1']}</td></tr><tr><td><strong>SHA-256:</strong></td><td>{dados_hash['sha256']}</td></tr></table></div>"""

        self.html_parts.append(
            f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Relatório {nome_instituicao}</title>{self.css}</head><body><div class="container"><div class="header">{img_tag}<h1>{nome_instituicao}</h1><h2>RELATÓRIO DE ANÁLISE - DADOS EXTRAÍDOS</h2><div class="meta-info">{tipo_envolvido}: <strong>{nome_dono}</strong> (ID: {id_dono})<br>FONTE: {arquivo_db}<br>DATA: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</div></div><div class="chat-box">{TEXTO_INTRODUCAO_TECNICA}{html_hash}<hr style="border:0;height:1px;background:#ddd;margin:20px 0;"><div class="search-bar"><input type="text" id="searchInput" onkeyup="filtrarChats()" placeholder="🔍 Busca por Chat ou Conteúdo: Digite para filtrar..." class="search-input"><div style="font-size:11px; color:#999; margin-top:5px;"><strong>Filtro Inteligente:</strong> O sistema oculta automaticamente os chats que não correspondem à pesquisa.</div></div>"""
        )

    def iniciar_container_chat(self, nome_chat, tid):
        self.html_parts.append(
            f"""<div class="chat-container"><div class="chat-container-header">Chat: {nome_chat} <br><span style="font-weight:normal;font-size:10px">(ID: {tid})</span></div><div class="chat-container-body">"""
        )

    def fechar_container_chat(self):
        self.html_parts.append("</div></div>")

    def adicionar_msg(
        self, texto, data, eh_dono, nome_rem, caminho_midia=None, transcricao=None
    ):
        css_wrapper = "sent" if eh_dono else "received"
        html_midia = ""
        html_transc = ""

        if transcricao:
            html_transc = f'<div class="transcription">🎙️ Transcrição automática (WHISPER OPENAI): "{transcricao}"</div>'

        if caminho_midia:
            link = f"file:///{caminho_midia}"
            nome_arq = os.path.basename(caminho_midia).lower()
            eh_audio = False
            if "voice_message" in nome_arq or nome_arq.endswith(
                (".opus", ".wav", ".mp3", ".amr", ".ogg", ".m4a")
            ):
                eh_audio = True

            if eh_audio:
                html_midia = f'<div class="audio-container"><audio controls><source src="{link}"></audio><br><a href="{link}" target="_blank" class="btn-open">Abrir Áudio</a></div>'
            elif nome_arq.endswith((".mp4", ".mov", ".3gp")):
                html_midia = f'<video controls width="250"><source src="{link}" type="video/mp4"></video><br><a href="{link}" target="_blank" class="btn-open">Abrir Vídeo</a>'
            else:
                html_midia = f'<div style="margin-top:10px;"><img src="{link}" style="cursor:pointer;" onclick="window.open(this.src)"></div>'

        display_nome = "" if eh_dono else f'<div class="sender-name">{nome_rem}</div>'
        self.html_parts.append(
            f"""<div class="msg-wrapper {css_wrapper}">{display_nome}<div class="msg"><span class="msg-text">{texto}{html_transc}</span>{html_midia}<div class="meta">{data}</div></div></div>"""
        )

    def finalizar(self, galeria):
        script_js = """<script>function filtrarChats(){var input=document.getElementById('searchInput').value.toUpperCase();var chats=document.getElementsByClassName('chat-container');for(var i=0;i<chats.length;i++){var txtValue=chats[i].textContent||chats[i].innerText;if(txtValue.toUpperCase().indexOf(input)>-1){chats[i].style.display="";}else{chats[i].style.display="none";}}}</script>"""
        self.html_parts.append(
            '</div><div class="stories-section"><h2 style="color:#833AB4;border-bottom:1px solid #eee">📸 Galeria de Evidências (Arquivos não vinculados)</h2>'
        )
        for item in galeria:
            link = f"file:///{item['caminho']}"
            nome = item["nome"]
            if "voice_message" in nome or nome.endswith((".m4a", ".opus")):
                prev = (
                    f'<audio controls style="width:200px"><source src="{link}"></audio>'
                )
            elif nome.endswith((".mp4", ".mov")):
                prev = f'<video width="150"><source src="{link}"></video>'
            else:
                prev = f'<img src="{link}" style="max-height:100%;max-width:100%">'
            self.html_parts.append(
                f'<div class="story-card"><div class="story-preview">{prev}</div><div class="story-info"><b>{item["nome"]}</b><br><a href="{link}" target="_blank" class="btn-open">Abrir</a></div></div>'
            )
        self.html_parts.append(f"{script_js}</div></div></body></html>")
        return "".join(self.html_parts)


# --- PROCESSAMENTO ---
def processar(
    db_path,
    pasta_backup,
    log_widget,
    nome_inst,
    path_logo,
    tipo_envolvido,
    usar_transcricao=False,
    modelo_whisper="small",
):
    model = None

    try:
        salvar_configuracoes(nome_inst, path_logo, tipo_envolvido)
        log_widget.insert(tk.END, f"Iniciando (v1.4)...\n")
        log_widget.update()
        logo_b64 = imagem_para_base64(path_logo)

        # --- CARREGAMENTO DO MODELO WHISPER SELECIONADO ---
        if usar_transcricao:
            if TEM_WHISPER:
                log_widget.insert(
                    tk.END, f"Iniciando IA (Modelo: {modelo_whisper})...\n"
                )
                if modelo_whisper in ["medium", "large"]:
                    log_widget.insert(
                        tk.END,
                        "⚠️ Atenção: Modelos grandes podem demorar MUITO para baixar e carregar.\n",
                    )
                log_widget.update()

                try:
                    original_stderr = sys.stderr
                    sys.stderr = RedirecionadorLog(log_widget)

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        # CARREGA O MODELO ESCOLHIDO PELO USUÁRIO
                        model = whisper.load_model(modelo_whisper, download_root=".")

                    sys.stderr = original_stderr
                    log_widget.insert(tk.END, "\n✅ IA Carregada com Sucesso!\n")
                except Exception as e:
                    sys.stderr = (
                        sys.__stderr__
                        if sys.__stderr__
                        else RedirecionadorLog(log_widget)
                    )
                    log_widget.insert(
                        tk.END, f"\nERRO CRÍTICO NA IA (SHA256 ou Rede): {e}\n"
                    )
                    model = None
            else:
                log_widget.insert(tk.END, "ERRO: Whisper não instalado.\n")
        # -------------------------------------------------------

        log_widget.insert(tk.END, "Calculando Hashes...\n")
        dados_hash = calcular_hashes_arquivo(db_path)

        log_widget.insert(tk.END, "Indexando Mídia e Voice Messages...\n")
        lista_voice, lista_geral, lista_sys, galeria = indexar_tudo(
            pasta_backup, log_widget
        )

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT thread_id, timestamp, user_id, text, message_type FROM messages ORDER BY timestamp ASC"
        )
        msgs_todas = cursor.fetchall()

        log_widget.insert(tk.END, "Executando Match Heurístico de Áudio...\n")
        mapa_audios_vinculados = realizar_match_heuristico(msgs_todas, lista_voice)
        log_widget.insert(
            tk.END, f"Áudios recuperados e vinculados: {len(mapa_audios_vinculados)}\n"
        )

        msgs_ordenadas = list(msgs_todas)
        msgs_ordenadas.sort(key=lambda x: (x[0], x[1]))

        try:
            cursor.execute(
                "SELECT user_id, COUNT(*) FROM messages GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 1"
            )
            dono_id = str(cursor.fetchone()[0])
        except:
            dono_id = "0"

        mapa_nomes = {dono_id: f"{tipo_envolvido.upper()} (Dono)"}
        thread_map = {}
        nome_investigado = "Desconhecido"
        try:
            cursor.execute("SELECT thread_id, thread_info FROM threads")
            for row in cursor.fetchall():
                try:
                    d = json.loads(row[1])
                    users = d.get("recipients") or d.get("users") or []
                    if d.get("inviter"):
                        users.append(d.get("inviter"))
                    parts = []
                    for u in users:
                        uid = str(u.get("id") or u.get("pk"))
                        nm = u.get("full_name") or u.get("username") or "Sem Nome"
                        if uid == dono_id:
                            nome_investigado = nm
                        else:
                            mapa_nomes[uid] = nm
                        if uid != dono_id:
                            parts.append(nm)
                    thread_map[row[0]] = ", ".join(list(set(parts)))
                except:
                    pass
        except:
            pass

        rel = RelatorioHTML()
        rel.iniciar(
            f"{nome_investigado}",
            dono_id,
            os.path.basename(db_path),
            nome_inst,
            logo_b64,
            tipo_envolvido,
            dados_hash,
        )

        midias_usadas = set()

        for tid, grupo_msgs in groupby(msgs_ordenadas, key=lambda x: x[0]):
            nome_chat = thread_map.get(tid, "Chat Desconhecido")
            rel.iniciar_container_chat(nome_chat, tid)

            for m in grupo_msgs:
                ts, uid, txt, mtype = m[1], str(m[2]), m[3], m[4]
                arq = None
                ts_ms = int(ts) / 1000 if int(ts) > 10000000000000 else int(ts)
                ts_ms = int(ts_ms)

                if ts_ms in mapa_audios_vinculados:
                    arq = mapa_audios_vinculados[ts_ms]
                elif mtype != "text":
                    arq = buscar_midia_comum(ts, lista_geral, lista_sys)

                # --- BLOCO DE TRANSCRIÇÃO ---
                texto_transcrito = None
                if arq and model is not None:
                    ext = os.path.splitext(arq)[1].lower()
                    if (
                        ext in [".mp4", ".m4a", ".opus", ".wav", ".mp3", ".ogg", ".amr"]
                        or "voice" in arq
                    ):
                        try:
                            log_widget.insert(
                                tk.END, f"Transc.: {os.path.basename(arq)}... "
                            )
                            log_widget.see(tk.END)
                            log_widget.update()

                            result = model.transcribe(arq, language="pt", fp16=False)
                            texto_transcrito = result["text"]

                            log_widget.insert(tk.END, "OK\n")
                        except Exception as e:
                            # ISSO VAI MOSTRAR O ERRO REAL NA TELA
                            log_widget.insert(tk.END, "FALHA\n")
                            log_widget.insert(tk.END, f"ERRO TÉCNICO: {str(e)}\n")
                            log_widget.see(tk.END)  # Rola para baixo para você ler
                # ---------------------------

                if arq:
                    midias_usadas.add(arq)
                if txt is None:
                    txt = f"[{mtype}]"
                d_str = (
                    datetime.datetime.fromtimestamp(ts_ms / 1000).strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                    if ts
                    else "--"
                )

                rel.adicionar_msg(
                    str(txt).replace("\n", "<br>"),
                    d_str,
                    (uid == dono_id),
                    mapa_nomes.get(uid, f"ID {uid}"),
                    arq,
                    texto_transcrito,
                )

            rel.fechar_container_chat()

        galeria_final = [x for x in galeria if x["caminho"] not in midias_usadas]
        html = rel.finalizar(galeria_final)
        conn.close()

        arquivo_final = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            initialfile=f"Relatorio_{nome_investigado}.html",
            title="Salvar Relatório",
        )

        if arquivo_final:
            with open(arquivo_final, "w", encoding="utf-8") as f:
                f.write(html)
            log_widget.insert(tk.END, "Gerando Lacre Digital do Relatório...\n")
            hash_relatorio = calcular_hashes_arquivo(arquivo_final)
            if hash_relatorio:
                arquivo_txt = os.path.splitext(arquivo_final)[0] + "_LACRE_DIGITAL.txt"
                texto_lacre = f"""=========================================================
          LACRE DE INTEGRIDADE DIGITAL
=========================================================
Este arquivo garante que o relatório HTML anexo não foi 
alterado após sua geração.

ARQUIVO ALVO: {os.path.basename(arquivo_final)}
DATA DA GERAÇÃO: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

--- ASSINATURAS DIGITAIS (HASHES) ---
MD5:    {hash_relatorio['md5']}
SHA-1:  {hash_relatorio['sha1']}
SHA-256:{hash_relatorio['sha256']}
=========================================================
"""
                with open(arquivo_txt, "w", encoding="utf-8") as f:
                    f.write(texto_lacre)
                log_widget.insert(tk.END, f"Lacre Gerado: {arquivo_txt}\n")
            log_widget.insert(tk.END, f"Salvo: {arquivo_final}\n")
            messagebox.showinfo("Sucesso", "Análise Concluída e Lacre Gerado!")

    except Exception as e:
        log_widget.insert(tk.END, f"ERRO GERAL: {e}\n")
        print(e)


# --- GUI ---
root = tk.Tk()
root.title("Analisador Forense Instagram - v1.4")
root.geometry("700x850")

try:
    root.iconbitmap(resource_path("icone.ico"))
except:
    pass

conf = carregar_configuracoes()
v_inst = tk.StringVar(value=conf.get("instituicao", ""))
v_logo = tk.StringVar(value=conf.get("logo_path", ""))
v_tipo = tk.StringVar(value=conf.get("tipo_envolvido", "Investigado"))
var_transcrever = tk.BooleanVar(value=False)
logos_disp = listar_logos_padrao()


def sdb():
    f = filedialog.askopenfilename(filetypes=[("Banco DB", "*.db"), ("Todos", "*.*")])
    if f:
        ldb.config(text=f)


def sdir():
    d = filedialog.askdirectory()
    if d:
        ldir.config(text=d)


def slogo():
    f = filedialog.askopenfilename(filetypes=[("IMG", "*.png *.jpg")])
    if f:
        v_logo.set(f)
        combo.set("")


def sel_logo(e):
    if combo.get():
        v_logo.set(os.path.abspath(os.path.join(PASTA_LOGOS, combo.get())))


def run():
    # Passa o modelo escolhido na combobox para a função
    processar(
        ldb.cget("text"),
        ldir.cget("text"),
        txt,
        v_inst.get(),
        v_logo.get(),
        v_tipo.get(),
        var_transcrever.get(),
        combo_modelo.get(),
    )


fr = tk.LabelFrame(root, text=" Configurações ", padx=10, pady=10)
fr.pack(fill="x", padx=10, pady=5)
tk.Label(fr, text="Instituição:").pack(anchor="w")
tk.Entry(fr, textvariable=v_inst).pack(fill="x")
tk.Label(fr, text="Tipo:").pack(anchor="w")
ttk.Combobox(
    fr, textvariable=v_tipo, values=["Investigado", "Vítima", "Testemunha"]
).pack(fill="x")
tk.Label(fr, text="Logo:").pack(anchor="w")
if logos_disp:
    combo = ttk.Combobox(fr, values=logos_disp, state="readonly")
    combo.pack(fill="x")
    combo.bind("<<ComboboxSelected>>", sel_logo)
else:
    combo = ttk.Combobox(fr, state="disabled")
    combo.pack(fill="x")
tk.Button(fr, text="Buscar Logo no PC...", command=slogo).pack(fill="x")
tk.Label(fr, textvariable=v_logo, fg="blue", font=("Arial", 8)).pack(anchor="w")

fr2 = tk.LabelFrame(root, text=" Arquivos ", padx=10, pady=10)
fr2.pack(fill="both", expand=True, padx=10)
tk.Label(fr2, text="1. Arquivo direct.db ou Data Base da extração:").pack(anchor="w")
ldb = tk.Label(fr2, text="...", fg="blue")
ldb.pack(anchor="w")
tk.Button(fr2, text="Selecionar DB", command=sdb).pack(fill="x")
tk.Label(fr2, text="2. Pasta raiz da extração:").pack(anchor="w")
ldir = tk.Label(fr2, text="...", fg="blue")
ldir.pack(anchor="w")
tk.Button(fr2, text="Selecionar Pasta", command=sdir).pack(fill="x")

# --- ÁREA DA TRANSCRIÇÃO (CHECKBOX + COMBOBOX) ---
frame_transc = tk.Frame(fr2)
frame_transc.pack(fill="x", pady=5)

chk_transc = tk.Checkbutton(
    frame_transc,
    text="Transcrever Áudios (IA)",
    variable=var_transcrever,
    fg="#b71c1c",
    font=("Arial", 9, "bold"),
)
chk_transc.pack(side="left")

tk.Label(frame_transc, text="Modelo:").pack(side="left", padx=(10, 2))
combo_modelo = ttk.Combobox(
    frame_transc, values=["small", "turbo"], state="readonly", width=10
)
combo_modelo.set("turbo")  # Já deixa o Turbo marcado como padrão
combo_modelo.pack(side="left")
# -------------------------------------------------

tk.Button(
    fr2, text="GERAR RELATÓRIO", command=run, bg="#b71c1c", fg="white", height=2
).pack(fill="x", pady=10)

tk.Button(
    root,
    text="📘 ABRIR MANUAL DE INSTRUÇÕES (PDF)",
    command=abrir_manual_pdf,
    bg="#333",
    fg="white",
).pack(fill="x", padx=20, pady=5)

txt = tk.Text(root, height=10, bg="#f4f4f4")
txt.pack(fill="both", padx=10, pady=5)
root.mainloop()
