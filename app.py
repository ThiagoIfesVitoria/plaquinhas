import streamlit as st
import pandas as pd
from PIL import Image
from io import BytesIO
from pathlib import Path
import base64
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
# FUNÇÕES DE BASE E PDF
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

def get_logo_base64():
    """Lê a imagem original para mostrar no preview web"""
    if ARQUIVO_LOGO.exists():
        with open(ARQUIVO_LOGO, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

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

        descricao = str(registro["Texto Central"]).strip()
        id2 = str(registro["Código Lateral"]).strip()

        desenhar_placa(pdf, x, y_base + PLACA_ALTURA, descricao, id2, logo)
        desenhar_placa(pdf, x, y_base, descricao, id2, logo)

    pdf.save()
    buffer.seek(0)
    return buffer

# ==========================================================
# INTERFACE WEB (STREAMLIT)
# ==========================================================
st.set_page_config(page_title="Gerador de Plaquinhas", page_icon="🏷️", layout="wide")

st.title("Gerador de Plaquinhas 🏷️")
st.write("Preencha a tabela. A ferramenta é universal: digite o texto central e o código lateral exatamente como quer que apareçam.")

# Divide a tela: Tabela na esquerda (70%) e Preview na direita (30%)
col_tabela, col_preview = st.columns([2.5, 1.5])

with col_tabela:
    st.subheader("1. Preencha os Dados")
    if "df_inicial" not in st.session_state:
        st.session_state.df_inicial = pd.DataFrame([{"Texto Central": "GERADOR 01", "Código Lateral": "GGERA-01"}])

    df_editado = st.data_editor(
        st.session_state.df_inicial,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Texto Central": st.column_config.TextColumn("Texto Central (Ex: NOME DA SALA) *", required=True),
            "Código Lateral": st.column_config.TextColumn("Código Lateral (Ex: ID-001) *", required=True),
        }
    )

    # Limpeza e validação dos dados
    df_valido = df_editado.copy()
    df_valido["Texto Central"] = df_valido["Texto Central"].astype(str).str.strip()
    df_valido["Código Lateral"] = df_valido["Código Lateral"].astype(str).str.strip()
    df_valido = df_valido[
        (df_valido["Texto Central"] != "") & (df_valido["Texto Central"] != "nan") &
        (df_valido["Código Lateral"] != "") & (df_valido["Código Lateral"] != "nan")
    ]

with col_preview:
    st.subheader("2. Pré-visualização")
    
    # Pega os dados da primeira linha válida para mostrar no preview
    texto_preview = "TEXTO AQUI"
    codigo_preview = "CÓDIGO"
    
    if len(df_valido) > 0:
        texto_preview = df_valido.iloc[0]["Texto Central"].upper()
        codigo_preview = df_valido.iloc[0]["Código Lateral"].upper()
        st.caption("Visualizando a primeira linha da tabela:")
    else:
        st.caption("Preencha a tabela para ver a pré-visualização.")

    # HTML/CSS para simular a plaquinha exatamente na mesma proporção do PDF
    logo_b64 = get_logo_base64()
    img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="width: 140px; transform: rotate(-90deg);">' if logo_b64 else 'LOGO'
    
    html_preview = f"""
    <div style="
        width: 100%; 
        aspect-ratio: 4.3 / 2.2; 
        background: #F5F5F5; 
        border-radius: 4px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: flex; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        overflow: hidden;
        border: 1px solid #ccc;
        margin-bottom: 20px;
    ">
        <!-- Lado Esquerdo (Logo) -->
        <div style="width: 15%; display: flex; align-items: center; justify-content: center; overflow: hidden;">
            {img_tag}
        </div>
        
        <!-- Centro (Texto Principal) -->
        <div style="flex-grow: 1; display: flex; align-items: center; justify-content: center; text-align: center; padding: 10px;">
            <span style="font-weight: 800; font-size: 1.5vw; color: #000; line-height: 1.2; word-break: break-word;">
                {texto_preview.replace(chr(10), '<br>')}
            </span>
        </div>
        
        <!-- Faixa Azul Direita (Código) -->
        <div style="width: 15%; background: #55A9CB; display: flex; align-items: center; justify-content: center;">
            <div style="transform: rotate(90deg); white-space: nowrap; font-weight: 800; font-size: 1.2vw; color: #000;">
                {codigo_preview}
            </div>
        </div>
    </div>
    """
    st.markdown(html_preview, unsafe_allow_html=True)

    # Botão de Geração e Download (abaixo do preview)
    st.write(f"**Total de plaquinhas:** {len(df_valido)}")
    if len(df_valido) > 0:
        if st.button("Gerar PDF Final", type="primary", use_container_width=True):
            with st.spinner("Construindo arquivo de impressão..."):
                pdf_buffer = gerar_pdf_buffer(df_valido)
                st.success("PDF Pronto!")
                st.download_button(
                    label="📥 Baixar Arquivo PDF",
                    data=pdf_buffer,
                    file_name="plaquinhas.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    else:
        st.button("Gerar PDF Final", disabled=True, use_container_width=True)