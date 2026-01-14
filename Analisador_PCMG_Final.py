import sqlite3
import datetime
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import bisect
import base64 # Necessário para ler o logo

# --- ÁREA DO LOGO (IMPORTANTE) ---
# COLE O CÓDIGO GIGANTE DENTRO DAS ASPAS ABAIXO:
LOGO_BASE64 = """
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
"""
# ---------------------------------

# --- CONFIGURAÇÕES ---
MARGEM_ERRO_MS = 60000       
TAMANHO_MINIMO_KB = 30       
NOME_INSTITUICAO = "Delegacia de Polícia Civil de Machado - MG"
ANO_MINIMO = 2015            
ANO_MAXIMO = 2029            

# --- ENGENHARIA DE DADOS ---

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

# --- INDEXAÇÃO ---

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
                
                lista_galeria.append({
                    'ts': melhor_ts,
                    'caminho': caminho,
                    'nome': file
                })

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

# --- RELATÓRIO HTML (COM LOGO) ---

class RelatorioHTML:
    def __init__(self):
        self.html_parts = []
        self.css = """
        <style>
            body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #e9ebee; margin: 0; padding: 20px; color: #1c1e21; }
            .container { max-width: 950px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); overflow: hidden; }
            
            /* HEADER COM LOGO */
            .header { background: #222; padding: 30px; border-bottom: 6px solid #b71c1c; color: white; text-align: center; }
            .pcmg-logo { max-height: 100px; margin-bottom: 15px; display: block; margin-left: auto; margin-right: auto; }
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
            
            /* Galeria */
            .stories-section { padding: 30px; border-top: 8px solid #833AB4; background: #fdfdfd; }
            .section-title { color: #833AB4; font-size: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px;}
            .story-card { background: #fff; border: 1px solid #e0e0e0; padding: 15px; margin-bottom: 15px; border-radius: 8px; display: flex; gap: 20px; align-items: center; transition: transform 0.2s; }
            .story-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            .story-preview { width: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #000; border-radius: 6px; overflow: hidden; min-height: 100px; padding: 5px;}
            .story-info { flex: 1; }
            
            img, video { max-width: 100%; max-height: 300px; display: block; border-radius: 8px; }
            audio { width: 250px; height: 40px; }
            
            /* Botão de Resgate */
            .btn-open {
                display: inline-block;
                margin-top: 8px;
                padding: 6px 12px;
                background-color: #333;
                color: #fff !important;
                text-decoration: none;
                font-size: 11px;
                border-radius: 4px;
                font-weight: bold;
                text-align: center;
                border: 1px solid #000;
                cursor: pointer;
            }
            .btn-open:hover { background-color: #555; }
            .help-text { font-size: 10px; color: #888; margin-top: 4px; font-style: italic; }

            .audio-container { margin-top: 8px; background: rgba(255,255,255,0.2); padding: 5px; border-radius: 10px; display: inline-block; }
            .received .audio-container { background: rgba(0,0,0,0.05); }
        </style>
        """

    def iniciar(self, nome_dono, id_dono, arquivo_db):
        # Insere o logo no HTML usando Base64
        img_tag = f'<img src="data:image/png;base64,{LOGO_BASE64}" class="pcmg-logo">' if len(LOGO_BASE64) > 100 else ""
        
        self.html_parts.append(f"""
        <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Relatório de Análise - PCMG</title>{self.css}</head>
        <body><div class="container"><div class="header">
            {img_tag}
            <h1>{NOME_INSTITUICAO}</h1>
            <h2>RELATÓRIO DE ANÁLISE - DADOS EXTRAÍDOS</h2>
            <div class="meta-info">
                INVESTIGADO: <strong>{nome_dono}</strong> (ID: {id_dono})<br>
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
            Visualização de todos os arquivos de mídia processados na pasta de backup.<br>
        </p>""")
        
        for item in lista_galeria:
            caminho = item['caminho']
            nome_arq = item['nome']
            link = f"file:///{caminho}"
            
            preview = ""
            if caminho.endswith(('.mp4', '.m4a', '.opus')):
                preview = f'''
                <video controls preload="metadata" width="150" height="100">
                    <source src="{link}" type="video/mp4">
                </video>
                <a href="{link}" download target="_blank" class="btn-open">⬇️ Baixar</a>
                '''
            else:
                preview = f'<img src="{link}" onclick="window.open(this.src)" style="cursor:pointer; max-height:100%; width:auto;">'

            self.html_parts.append(f"""
            <div class="story-card">
                <div class="story-preview">{preview}</div>
                <div class="story-info">
                    <p style="font-size:12px; margin:0; font-weight:bold;">{nome_arq}</p>
                </div>
            </div>
            """)
    
        self.html_parts.append("</div></div></body></html>")
        return "".join(self.html_parts)

# --- PROCESSAMENTO ---

def processar(db_path, pasta_backup, log_widget):
    try:
        log_widget.insert(tk.END, f"Iniciando Análise de Dados (v1.0 - Oficial)...\n")
        log_widget.update()

        log_widget.insert(tk.END, f"Mapeando arquivos de mídia...\n")
        cn, idx_n, cs, idx_s, galeria = indexar_tudo(pasta_backup, log_widget)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, COUNT(*) FROM messages GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 1")
        try: dono_id = str(cursor.fetchone()[0])
        except: dono_id = "0"

        mapa_nomes = {dono_id: "DONO (Investigado)"}
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
        rel.iniciar(f"{nome_investigado} (Investigado)", dono_id, os.path.basename(db_path))

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

            rel.adicionar_msg(
                str(txt).replace('\n', '<br>'), d_str,
                (uid == dono_id), mapa_nomes.get(uid, f"ID {uid}"), arq
            )
        
        galeria_final = [x for x in galeria if x['caminho'] not in midias_usadas_chat]
        
        html = rel.finalizar(galeria_final)
        conn.close()

        arquivo_final = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("HTML", "*.html")],
            initialfile=f"Relatorio_Analise_{nome_investigado.replace(' ', '_')}.html", title="Salvar Relatório"
        )
        
        if arquivo_final:
            with open(arquivo_final, "w", encoding="utf-8") as f: f.write(html)
            log_widget.insert(tk.END, f"CONCLUÍDO!\nSalvo em: {arquivo_final}\n")
            messagebox.showinfo("Sucesso", "Análise Concluída e Relatório Gerado!")

    except Exception as e:
        log_widget.insert(tk.END, f"ERRO: {e}\n")
        print(e)

# --- GUI ---
root = tk.Tk()
root.title(f"PCMG - Analisador Forense de Dados")
root.geometry("650x600")

# Tratamento do Logo na GUI
try:
    if len(LOGO_BASE64) > 100:
        logo_data = base64.b64decode(LOGO_BASE64)
        logo_img = tk.PhotoImage(data=logo_data)
        # Redimensiona se for muito grande (opcional, ajusta visual)
        logo_img = logo_img.subsample(2, 2) 
        root.iconphoto(False, logo_img) # Define icone da janela
    else:
        logo_img = None
except:
    logo_img = None

def sdb():
    f = filedialog.askopenfilename()
    if f: ldb.config(text=f)
def sdir():
    d = filedialog.askdirectory()
    if d: ldir.config(text=d)
def r(): processar(ldb.cget("text"), ldir.cget("text"), txt)

frame_topo = tk.Frame(root, bg="#1a1a1a", pady=20)
frame_topo.pack(fill="x")

# Exibe o logo se estiver carregado
if logo_img:
    lbl_logo = tk.Label(frame_topo, image=logo_img, bg="#1a1a1a")
    lbl_logo.pack(pady=(0, 10))

tk.Label(frame_topo, text=NOME_INSTITUICAO, font=("Arial", 14, "bold"), fg="white", bg="#1a1a1a").pack()
tk.Label(frame_topo, text="Analisador de Dados Extraídos (Pós-Extração)", font=("Arial", 10), fg="#aaa", bg="#1a1a1a").pack()

frame_corpo = tk.Frame(root, padx=20, pady=20)
frame_corpo.pack(fill="both", expand=True)

tk.Label(frame_corpo, text="1. Selecione o arquivo 'direct.db' extraído:", font=("Arial", 10, "bold")).pack(anchor="w")
ldb = tk.Label(frame_corpo, text="...", fg="gray", wraplength=600); ldb.pack(anchor="w", pady=(0,5))
ttk.Button(frame_corpo, text="Buscar Banco de Dados", command=sdb).pack(fill="x", pady=(0,15))

tk.Label(frame_corpo, text="2. Selecione a Pasta do Backup (Raiz):", font=("Arial", 10, "bold")).pack(anchor="w")
ldir = tk.Label(frame_corpo, text="...", fg="gray", wraplength=600); ldir.pack(anchor="w", pady=(0,5))
ttk.Button(frame_corpo, text="Buscar Pasta de Mídia", command=sdir).pack(fill="x", pady=(0,20))

btn = tk.Button(frame_corpo, text="GERAR RELATÓRIO DE ANÁLISE", command=r, bg="#b71c1c", fg="white", font=("Arial", 11, "bold"), height=2)
btn.pack(fill="x")

txt = tk.Text(root, height=8, bg="#eee"); txt.pack(fill="both", padx=10, pady=10)

root.mainloop()