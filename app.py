import streamlit as st
import pandas as pd
from PIL import Image
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.lib.units import cm, mm

# ==========================================================
# CONFIGURAÇÕES DE LAYOUT
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ARQUIVO_LOGO = ASSETS_DIR / "logo.png"
FONTE_BOLD = ASSETS_DIR / "OpenSans-Bold.ttf"

PLACA_LARGURA = 4.3 * cm
PLACA_ALTURA = 2.2 * cm
TAMANHO_DESCRICAO = 10.1
TAMANHO_ID2 = 8.9
MARGEM_X = 8 * mm
MARGEM_Y = 8 * mm
ESPACO_X = 3 * mm
ESPACO_Y = 3 * mm
AZUL = HexColor("#55A9CB")
FUNDO = HexColor("#F5F5F5")
LARGURA_LOGO = 0.65 * cm
LARGURA_ID2 = 0.65 * cm

# ==========================================================
# FUNÇÕES DE BASE
# ==========================================================
def registrar_fontes():
    if not FONTE_BOLD.exists():
        st.error(f"Fonte não encontrada: {FONTE_BOLD}. Coloque na pasta assets.")
        st.stop()
    pdfmetrics.registerFont(TTFont("OpenSans-Bold", str(FONTE_BOLD)))

def preparar_logo():
    if not ARQUIVO_LOGO.exists():
        st.error(f"Logo não encontrado: {ARQUIVO_LOGO}.")
        st.stop()
    imagem = Image.open(ARQUIVO_LOGO).convert("RGBA").rotate(90, expand=True)
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)

def desenhar_placa(pdf, x, y, descricao, id2, logo):
    w, h = PLACA_LARGURA, PLACA_ALTURA
    pdf.saveState()
    pdf.setFillColor(FUNDO)
    pdf.rect(x, y, w, h, fill=1, stroke=0)
    
    pdf.setFillColor(AZUL)
    pdf.rect(x + w - LARGURA_ID2, y, LARGURA_ID2, h, fill=1, stroke=0)

    logo_w, logo_h = 0.43 * cm, 1.74 * cm
    pdf.drawImage(logo, x + (LARGURA_LOGO - logo_w) / 2, y + (h - logo_h) / 2, width=logo_w, height=logo_h, preserveAspectRatio=True, mask="auto")

    area_x = x + LARGURA_LOGO + 0.04 * cm
    area_largura = w - LARGURA_LOGO - LARGURA_ID2 - 0.08 * cm
    tamanho_fonte = TAMANHO_DESCRICAO

    linhas = simpleSplit(descricao.upper(), "OpenSans-Bold", tamanho_fonte, area_largura)
    while len(linhas) > 3 and tamanho_fonte > 6:
        tamanho_fonte -= 0.3
        linhas = simpleSplit(descricao.upper(), "OpenSans-Bold", tamanho_fonte, area_largura)

    pdf.setFillColor(HexColor("#000000"))
    pdf.setFont("OpenSans-Bold", tamanho_fonte)
    entrelinha = tamanho_fonte * 1.25
    altura_texto = len(linhas) * entrelinha
    centro_x = area_x + area_largura / 2
    inicio_y = y + (h + altura_texto) / 2 - entrelinha

    for i, linha in enumerate(linhas):
        pdf.drawCentredString(centro_x, inicio_y - i * entrelinha, linha)

    pdf.saveState()
    pdf.translate(x + w - LARGURA_ID2 / 2, y + h / 2)
    pdf.rotate(90)
    pdf.setFillColor(HexColor("#000000"))
    pdf.setFont("OpenSans-Bold", TAMANHO_ID2)
    pdf.drawCentredString(0, -TAMANHO_ID2 * 0.32, id2.upper())
    pdf.restoreState()
    pdf.restoreState()

def gerar_pdf_buffer(df):
    registrar_fontes()
    logo = preparar_logo()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    
    pagina_largura, pagina_altura = A4
    colunas = int((pagina_largura - 2 * MARGEM_X + ESPACO_X) // (PLACA_LARGURA + ESPACO_X))
    ALTURA_PAR = 2 * PLACA_ALTURA
    linhas_pares_por_pagina = int((pagina_altura - 2 * MARGEM_Y + ESPACO_Y) // (ALTURA_PAR + ESPACO_Y))
    capacidade = colunas * linhas_pares_por_pagina

    for indice, (_, registro) in enumerate(df.iterrows()):
        posicao_pagina = indice % capacidade
        if indice > 0 and posicao_pagina == 0:
            pdf.showPage()

        coluna = posicao_pagina % colunas
        linha_par = posicao_pagina // colunas
        x = MARGEM_X + coluna * (PLACA_LARGURA + ESPACO_X)
        y_base = pagina_altura - MARGEM_Y - ALTURA_PAR - linha_par * (ALTURA_PAR + ESPACO_Y)

        descricao = str(registro["Descrição"]).strip()
        id2 = str(registro["ID2"]).strip()

        desenhar_placa(pdf, x, y_base + PLACA_ALTURA, descricao, id2, logo)
        desenhar_placa(pdf, x, y_base, descricao, id2, logo)

    pdf.save()
    buffer.seek(0)
    return buffer

# ==========================================================
# INTERFACE WEB (STREAMLIT)
# ==========================================================
st.set_page_config(page_title="Gerador de Plaquinhas Vports", page_icon="🏷️", layout="centered")

st.title("Gerador de Plaquinhas 🏷️")
st.write("Preencha a tabela abaixo com os dados das plaquinhas. Para adicionar novas linhas, basta preencher a última linha vazia ou clicar no símbolo de **+**.")

# Inicia um DataFrame vazio com as colunas corretas (uma linha em branco para facilitar)
if "df_inicial" not in st.session_state:
    st.session_state.df_inicial = pd.DataFrame([{"Grupo": "", "Descrição": "", "ID": "", "ID2": ""}])

# Cria o editor de dados na tela (o usuário pode editar, adicionar ou excluir linhas)
df_editado = st.data_editor(
    st.session_state.df_inicial,
    num_rows="dynamic", # Permite ao usuário adicionar novas linhas dinamicamente
    use_container_width=True,
    hide_index=True,
    column_config={
        "Grupo": st.column_config.TextColumn("Grupo (Opcional)"),
        "Descrição": st.column_config.TextColumn("Descrição *", required=True),
        "ID": st.column_config.TextColumn("ID (Opcional)"),
        "ID2": st.column_config.TextColumn("ID2 *", required=True),
    }
)

# Filtra a tabela para garantir que não vamos tentar desenhar placas vazias
df_valido = df_editado.copy()
df_valido["Descrição"] = df_valido["Descrição"].astype(str).str.strip()
df_valido["ID2"] = df_valido["ID2"].astype(str).str.strip()

# Remove linhas onde Descrição ou ID2 estejam em branco (ou nan)
df_valido = df_valido[
    (df_valido["Descrição"] != "") & (df_valido["Descrição"] != "nan") &
    (df_valido["ID2"] != "") & (df_valido["ID2"] != "nan")
]

st.write(f"**Plaquinhas válidas prontas para geração:** {len(df_valido)}")

if len(df_valido) > 0:
    if st.button("Gerar PDF", type="primary"):
        with st.spinner("Desenhando as plaquinhas..."):
            pdf_buffer = gerar_pdf_buffer(df_valido)
            
            st.success("PDF gerado com sucesso!")
            st.download_button(
                label="📥 Baixar Arquivo PDF",
                data=pdf_buffer,
                file_name="plaquinhas.pdf",
                mime="application/pdf"
            )
elif st.button("Gerar PDF", disabled=True):
    pass