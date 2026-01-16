import sqlite3
import datetime
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import bisect
import base64

# --- CONFIGURAÇÕES GERAIS ---
MARGEM_ERRO_MS = 60000       
TAMANHO_MINIMO_KB = 30       
ANO_MINIMO = 2015            
ANO_MAXIMO = 2029            
ARQUIVO_CONFIG = "config_forense.json"

# --- UTILITÁRIOS DE CONFIGURAÇÃO ---

def carregar_configuracoes():
    padrao = {
        "instituicao": "Delegacia de Polícia Civil",
        "logo_path": "",
        "tipo_envolvido": "Investigado" # Padrão
    }
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                conf = json.load(f)
                
                for k, v in padrao.items():
                    if k not in conf: conf[k] = v
                return conf
        except:
            return padrao
    return padrao

def salvar_configuracoes(instituicao, logo_path, tipo_envolvido):
    dados = {
        "instituicao": instituicao,
        "logo_path": logo_path,
        "tipo_envolvido": tipo_envolvido
    }
    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar config: {e}")

def imagem_para_base64(caminho_imagem):
    if not caminho_imagem or not os.path.exists(caminho_imagem):
        return ""
    try:
        with open(caminho_imagem, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            ext = os.path.splitext(caminho_imagem)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            return f"data:image/{ext};base64,{encoded_string}"
    except:
        return ""

# --- ENGENHARIA DE DADOS  ---

def obter_timestamp_sistema(caminho):
    try: return int(os.path.getmtime(caminho) * 1000)
    except: return 0

def analisar_arquivo_midia(caminho):
    nome_arquivo = os.path.basename(caminho)
    ts_nome = None
    ts_sistema = obter_timestamp_sistema(caminho)
    
    matches = re.findall(r'(1[5-9]\d{11})', nome_arquivo)
    for match in matches:
        ts = int(match)
        try:
            ano = datetime.datetime.fromtimestamp(ts/1000.0).year
            if ANO_MINIMO <= ano <= ANO_MAXIMO:
                ts_nome = ts
                break
        except: pass
    
    if not ts_nome:
        match_data = re.search(r'(20[1-2][0-9])(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])', nome_arquivo)
        if match_data:
            try:
                dt = datetime.datetime(int(match_data.group(1)), int(match_data.group(2)), int(match_data.group(3)), 12, 0)
                ts_nome = int(dt.timestamp() * 1000)
            except: pass

    eh_valido_chat = False
    if ts_nome: eh_valido_chat = True
    elif ts_sistema > 0:
        try:
            ano_sys = datetime.datetime.fromtimestamp(ts_sistema/1000.0).year
            if ANO_MINIMO <= ano_sys <= ANO_MAXIMO:
                eh_valido_chat = True
        except: pass

    return ts_nome, ts_sistema, eh_valido_chat

def indexar_tudo(pasta_backup, log_widget):
    index_por_nome = {}   
    chaves_nome = []
    index_por_sistema = {} 
    chaves_sistema = []
    lista_galeria = []
    count_total = 0
    
    for root, dirs, files in os.walk(pasta_backup):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.m4a', '.opus', '.wav', '.mp3', '.webp')):
                caminho = os.path.join(root, file).replace("\\", "/")
                tamanho = os.path.getsize(caminho)
                if tamanho < (TAMANHO_MINIMO_KB * 1024): continue
                
                count_total += 1
                ts_nome, ts_sistema, valido_chat = analisar_arquivo_midia(caminho)
                
                if valido_chat:
                    if ts_nome:
                        index_por_nome[ts_nome] = caminho
                        chaves_nome.append(ts_nome)
                    if ts_sistema:
                        if ts_sistema not in index_por_sistema:
                            index_por_sistema[ts_sistema] = caminho
                            chaves_sistema.append(ts_sistema)

                melhor_ts = ts_nome if ts_nome else ts_sistema
                lista_galeria.append({'ts': melhor_ts, 'caminho': caminho, 'nome': file})

    chaves_nome.sort()
    chaves_sistema.sort()
    log_widget.insert(tk.END, f"Arquivos processados: {count_total}\n")
    return chaves_nome, index_por_nome, chaves_sistema, index_por_sistema, lista_galeria

def buscar_midia_hibrida(ts_msg, chaves_nome, idx_nome, chaves_sys, idx_sys):
    if not ts_msg: return None
    t_alvo = int(ts_msg)
    if t_alvo > 10000000000000: t_alvo = int(t_alvo/1000)

    def buscar_na_lista(chaves, indice):
        if not chaves: return None
        pos = bisect.bisect_left(chaves, t_alvo)
        candidatos = []
        if pos > 0:
            ts = chaves[pos-1]
            diff = abs(ts - t_alvo)
            if diff <= MARGEM_ERRO_MS: candidatos.append((diff, ts))
        if pos < len(chaves):
            ts = chaves[pos]
            diff = abs(ts - t_alvo)
            if diff <= MARGEM_ERRO_MS: candidatos.append((diff, ts))
        if candidatos:
            candidatos.sort(key=lambda x: x[0])
            return indice[candidatos[0][1]]
        return None

    res = buscar_na_lista(chaves_nome, idx_nome)
    if res: return res
    return buscar_na_lista(chaves_sys, idx_sys)

# --- RELATÓRIO HTML ---

class RelatorioHTML:
    def __init__(self):
        self.html_parts = []
        self.css = """
        <style>
            body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #e9ebee; margin: 0; padding: 20px; color: #1c1e21; }
            .container { max-width: 950px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); overflow: hidden; }
            .header { background: #222; padding: 30px; border-bottom: 6px solid #b71c1c; color: white; text-align: center; }
            .pcmg-logo { max-height: 120px; max-width: 100%; margin-bottom: 15px; display: block; margin-left: auto; margin-right: auto; object-fit: contain; }
            .header h1 { margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 800; }
            .header h2 { margin: 8px 0 0; font-size: 15px; font-weight: 400; color: #ddd; }
            .meta-info { margin-top: 20px; font-size: 13px; color: #ccc; line-height: 1.6; border: 1px solid #444; display: inline-block; padding: 10px 20px; border-radius: 4px; background: #333;}
            .chat-box { padding: 30px; display: flex; flex-direction: column; gap: 15px; background: #fff; }
            .msg { max-width: 80%; padding: 12px 18px; border-radius: 18px; font-size: 14px; position: relative; line-height: 1.5; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .sent { align-self: flex-end; background-color: #0084ff; color: white; border-bottom-right-radius: 2px; }
            .received { align-self: flex-start; background-color: #f0f2f5; color: #050505; border-bottom-left-radius: 2px; border: 1px solid #ddd;}
            .sender-name { font-size: 11px; color: #666; margin-left: 12px; margin-bottom: 2px; font-weight: 700; }
            .meta { font-size: 10px; margin-top: 5px; opacity: 0.7; text-align: right; }
            .thread-divider { text-align: center; margin: 60px 0 20px; color: #555; font-size: 13px; font-weight: bold; border-top: 2px solid #eee; padding-top: 20px; text-transform: uppercase; letter-spacing: 0.5px;}
            .stories-section { padding: 30px; border-top: 8px solid #833AB4; background: #fdfdfd; }
            .section-title { color: #833AB4; font-size: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px;}
            .story-card { background: #fff; border: 1px solid #e0e0e0; padding: 15px; margin-bottom: 15px; border-radius: 8px; display: flex; gap: 20px; align-items: center; transition: transform 0.2s; }
            .story-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            .story-preview { width: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #000; border-radius: 6px; overflow: hidden; min-height: 100px; padding: 5px;}
            .story-info { flex: 1; }
            img, video { max-width: 100%; max-height: 300px; display: block; border-radius: 8px; }
            audio { width: 250px; height: 40px; }
            .btn-open { display: inline-block; margin-top: 8px; padding: 6px 12px; background-color: #333; color: #fff !important; text-decoration: none; font-size: 11px; border-radius: 4px; font-weight: bold; text-align: center; border: 1px solid #000; cursor: pointer; }
            .btn-open:hover { background-color: #555; }
            .audio-container { margin-top: 8px; background: rgba(255,255,255,0.2); padding: 5px; border-radius: 10px; display: inline-block; }
            .received .audio-container { background: rgba(0,0,0,0.05); }
        </style>
        """

    def iniciar(self, nome_dono, id_dono, arquivo_db, nome_instituicao, logo_src, tipo_envolvido):
        img_tag = f'<img src="{logo_src}" class="pcmg-logo">' if logo_src else ""
        label_tipo = tipo_envolvido.upper() if tipo_envolvido else "INVESTIGADO"
        
        self.html_parts.append(f"""
        <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Relatório - {nome_instituicao}</title>{self.css}</head>
        <body><div class="container"><div class="header">
            {img_tag}
            <h1>{nome_instituicao}</h1>
            <h2>RELATÓRIO DE ANÁLISE - DADOS EXTRAÍDOS</h2>
            <div class="meta-info">
                {label_tipo}: <strong>{nome_dono}</strong> (ID: {id_dono})<br>
                FONTE ANALISADA: {arquivo_db}<br>
                DATA DA ANÁLISE: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
            </div>
        </div><div class="chat-box">
        """)

    def adicionar_separador(self, nome, tid):
        self.html_parts.append(f'<div class="thread-divider">Conversa com: <span style="color:#000;">{nome}</span><br><span style="font-size:10px; font-weight:normal; color:#999;">ID: {tid}</span></div>')

    def adicionar_msg(self, texto, data, eh_dono, nome_rem, caminho_midia=None):
        css = "sent" if eh_dono else "received"
        html_midia = ""
        if caminho_midia:
            link = f"file:///{caminho_midia}"
            if caminho_midia.endswith(('.mp4', '.m4a', '.opus', '.wav', '.mp3')):
                html_midia = f'''
                <div class="audio-container">
                    <audio controls><source src="{link}" type="video/mp4"></audio>
                    <br>
                    <a href="{link}" download target="_blank" class="btn-open">⬇️ Salvar / Abrir Externo</a>
                </div>'''
            else:
                html_midia = f'<div style="margin-top:10px;"><img src="{link}" style="cursor:pointer;" onclick="window.open(this.src)"></div>'

        display_nome = "" if eh_dono else f'<div class="sender-name">{nome_rem}</div>'
        self.html_parts.append(f"""
            {display_nome}
            <div class="msg {css}">
                {texto}
                {html_midia}
                <div class="meta">{data}</div>
            </div>
        """)

    def finalizar(self, lista_galeria):
        lista_galeria.sort(key=lambda x: x['ts'], reverse=True)
        self.html_parts.append(f"""
        </div><div class="stories-section">
        <h2 class="section-title">📸 Galeria de Evidências (Mídias Encontradas)</h2>
        <p style="color:#666; font-size:13px; margin-bottom:25px; line-height:1.5;">
            Visualização de todos os arquivos de mídia processados.<br>
        </p>""")
        for item in lista_galeria:
            caminho = item['caminho']
            nome_arq = item['nome']
            link = f"file:///{caminho}"
            preview = ""
            if caminho.endswith(('.mp4', '.m4a', '.opus')):
                preview = f'<video controls preload="metadata" width="150" height="100"><source src="{link}" type="video/mp4"></video><a href="{link}" download target="_blank" class="btn-open">⬇️ Baixar</a>'
            else:
                preview = f'<img src="{link}" onclick="window.open(this.src)" style="cursor:pointer; max-height:100%; width:auto;">'

            self.html_parts.append(f"""
            <div class="story-card">
                <div class="story-preview">{preview}</div>
                <div class="story-info"><p style="font-size:12px; margin:0; font-weight:bold;">{nome_arq}</p></div>
            </div>""")
        self.html_parts.append("</div></div></body></html>")
        return "".join(self.html_parts)

# --- PROCESSAMENTO ---

def processar(db_path, pasta_backup, log_widget, nome_inst, path_logo, tipo_envolvido):
    try:
        salvar_configuracoes(nome_inst, path_logo, tipo_envolvido)
        log_widget.insert(tk.END, f"Iniciando Análise (v2.1 - {tipo_envolvido})...\n")
        log_widget.update()
        logo_b64 = imagem_para_base64(path_logo)

        log_widget.insert(tk.END, f"Mapeando arquivos de mídia...\n")
        cn, idx_n, cs, idx_s, galeria = indexar_tudo(pasta_backup, log_widget)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, COUNT(*) FROM messages GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 1")
        try: dono_id = str(cursor.fetchone()[0])
        except: dono_id = "0"

        mapa_nomes = {dono_id: f"{tipo_envolvido.upper()} (Dono do Device)"}
        thread_map = {}
        nome_investigado = "Nome não identificado"

        cursor.execute("SELECT thread_id, thread_info FROM threads")
        for row in cursor.fetchall():
            try:
                d = json.loads(row[1])
                parts = []
                users = d.get('recipients') or d.get('users') or []
                if d.get('inviter'): users.append(d.get('inviter'))
                for u in users:
                    uid = str(u.get('id') or u.get('pk'))
                    nome = u.get('full_name') or u.get('username') or "Sem Nome"
                    if uid == dono_id: nome_investigado = nome
                    else: mapa_nomes[uid] = nome
                    if uid != dono_id: parts.append(nome)
                thread_map[row[0]] = ", ".join(list(set(parts))) 
            except: pass

        rel = RelatorioHTML()
        rel.iniciar(f"{nome_investigado} ({tipo_envolvido})", dono_id, os.path.basename(db_path), nome_inst, logo_b64, tipo_envolvido)

        cursor.execute("SELECT thread_id, timestamp, user_id, text, message_type FROM messages ORDER BY thread_id, timestamp ASC")
        msgs = cursor.fetchall()
        curr_t = None
        midias_usadas_chat = set()

        for m in msgs:
            tid, ts, uid, txt, mtype = m
            uid = str(uid)
            if tid != curr_t:
                rel.adicionar_separador(thread_map.get(tid, "Desconhecido"), tid)
                curr_t = tid
            arq = None
            if mtype != 'text':
                arq = buscar_midia_hibrida(ts, cn, idx_n, cs, idx_s)
                if arq: midias_usadas_chat.add(arq)
            if txt is None: txt = f"[{mtype}]"
            d_str = datetime.datetime.fromtimestamp(int(ts)/1000000).strftime('%d/%m/%Y %H:%M:%S') if ts else "--"
            rel.adicionar_msg(str(txt).replace('\n', '<br>'), d_str, (uid == dono_id), mapa_nomes.get(uid, f"ID {uid}"), arq)
        
        galeria_final = [x for x in galeria if x['caminho'] not in midias_usadas_chat]
        html = rel.finalizar(galeria_final)
        conn.close()

        arquivo_final = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("HTML", "*.html")],
            initialfile=f"Relatorio_{tipo_envolvido}_{nome_investigado.replace(' ', '_')}.html", title="Salvar Relatório"
        )
        if arquivo_final:
            with open(arquivo_final, "w", encoding="utf-8") as f: f.write(html)
            log_widget.insert(tk.END, f"CONCLUÍDO!\nSalvo em: {arquivo_final}\n")
            messagebox.showinfo("Sucesso", "Análise Concluída!")

    except Exception as e:
        log_widget.insert(tk.END, f"ERRO: {e}\n")
        print(e)

# --- GUI ---
root = tk.Tk()
root.title(f"Analisador Forense de Dados do Instagram")
root.geometry("700x780")

configs_iniciais = carregar_configuracoes()
var_instituicao = tk.StringVar(value=configs_iniciais.get("instituicao", ""))
var_logo_path = tk.StringVar(value=configs_iniciais.get("logo_path", ""))
var_tipo_envolvido = tk.StringVar(value=configs_iniciais.get("tipo_envolvido", "Investigado"))

def sdb():
    f = filedialog.askopenfilename(filetypes=[("Banco de Dados", "*.db"), ("Todos", "*.*")])
    if f: ldb.config(text=f)
def sdir():
    d = filedialog.askdirectory()
    if d: ldir.config(text=d)
def slogo():
    f = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg")])
    if f: var_logo_path.set(f)
def r(): 
    processar(ldb.cget("text"), ldir.cget("text"), txt, var_instituicao.get(), var_logo_path.get(), var_tipo_envolvido.get())

# FRAME DE PERSONALIZAÇÃO
frame_config = tk.LabelFrame(root, text=" ⚙️ Personalização do Relatório ", padx=15, pady=15, font=("Arial", 10, "bold"), fg="#333")
frame_config.pack(fill="x", padx=10, pady=10)

tk.Label(frame_config, text="Nome da Instituição / Delegacia:", font=("Arial", 9)).pack(anchor="w")
entry_inst = tk.Entry(frame_config, textvariable=var_instituicao, font=("Arial", 10))
entry_inst.pack(fill="x", pady=(0, 10))

# Seletor de Tipo (NOVO)
tk.Label(frame_config, text="Tipo de Envolvido (Dono do Celular):", font=("Arial", 9)).pack(anchor="w")
combo_tipo = ttk.Combobox(frame_config, textvariable=var_tipo_envolvido, 
                          values=["Investigado", "Vítima", "Testemunha"], 
                          state="normal") 
combo_tipo.pack(fill="x", pady=(0, 10))

tk.Label(frame_config, text="Logo do Relatório (Imagem .PNG ou .JPG):", font=("Arial", 9)).pack(anchor="w")
frame_logo_sel = tk.Frame(frame_config)
frame_logo_sel.pack(fill="x")
tk.Button(frame_logo_sel, text="Selecionar Imagem", command=slogo, font=("Arial", 9)).pack(side="left")
tk.Label(frame_logo_sel, textvariable=var_logo_path, fg="gray", font=("Arial", 8)).pack(side="left", padx=10)

# FRAME PRINCIPAL
frame_corpo = tk.LabelFrame(root, text=" 📂 Dados da Investigação ", padx=15, pady=15, font=("Arial", 10, "bold"), fg="#333")
frame_corpo.pack(fill="both", expand=True, padx=10, pady=5)

tk.Label(frame_corpo, text="1. Selecione o arquivo 'direct.db' extraído:", font=("Arial", 10)).pack(anchor="w")
ldb = tk.Label(frame_corpo, text="...", fg="blue", wraplength=600, justify="left"); ldb.pack(anchor="w", pady=(0,5))
ttk.Button(frame_corpo, text="Buscar Banco de Dados", command=sdb).pack(fill="x", pady=(0,15))

tk.Label(frame_corpo, text="2. Selecione a Pasta do Backup (Raiz):", font=("Arial", 10)).pack(anchor="w")
ldir = tk.Label(frame_corpo, text="...", fg="blue", wraplength=600, justify="left"); ldir.pack(anchor="w", pady=(0,5))
ttk.Button(frame_corpo, text="Buscar Pasta de Mídia", command=sdir).pack(fill="x", pady=(0,20))

btn = tk.Button(frame_corpo, text="GERAR RELATÓRIO DE ANÁLISE", command=r, bg="#b71c1c", fg="white", font=("Arial", 11, "bold"), height=2)
btn.pack(fill="x")

# LOG
frame_log = tk.Frame(root, padx=10, pady=10)
frame_log.pack(fill="both", expand=True)
txt = tk.Text(frame_log, height=8, bg="#f4f4f4", font=("Consolas", 9)); txt.pack(fill="both", expand=True)

root.mainloop()