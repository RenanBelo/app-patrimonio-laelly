import streamlit as st
import pandas as pd
import cv2
import numpy as np
import easyocr
import re

# Configuração da página
st.set_page_config(page_title="Scanner de Patrimônio", layout="centered")

# Inicializa o armazenamento de dados na sessão
if 'registros' not in st.session_state:
    st.session_state.registros = []

# Inicializa a memória para não duplicar a mesma foto
if 'ultimo_arquivo_id' not in st.session_state:
    st.session_state.ultimo_arquivo_id = None

# Carrega a IA de leitura de texto (cache para não recarregar a cada foto)
@st.cache_resource
def carregar_leitor():
    return easyocr.Reader(['pt', 'en'])

leitor_texto = carregar_leitor()

st.title("📦 Scanner de Patrimônio")
st.write("Selecione a categoria e tire uma foto do NÚMERO do patrimônio.")

# Seleção da Categoria 
opcoes_categorias = ["Mesas", "Cadeiras", "Estantes", "Ar-Condicionado", "Informática", "Nova Categoria..."]
escolha_categoria = st.selectbox("Categoria do Item:", opcoes_categorias)

if escolha_categoria == "Nova Categoria...":
    categoria_selecionada = st.text_input("Digite o nome da nova categoria:")
else:
    categoria_selecionada = escolha_categoria

def processar_imagem(foto_arquivo):
    if not categoria_selecionada:
        st.warning("Por favor, digite o nome da categoria antes de enviar a foto.")
        return
        
    # --- TRAVA DE SEGURANÇA CONTRA DUPLICAÇÃO ---
    # Verifica se esta foto exata já foi lida antes
    if st.session_state.ultimo_arquivo_id == foto_arquivo.file_id:
        return # Interrompe a função, pois já processou essa imagem
    # ---------------------------------------------

    file_bytes = np.asarray(bytearray(foto_arquivo.read()), dtype=np.uint8)
    imagem = cv2.imdecode(file_bytes, 1)
    
    with st.spinner('Lendo a imagem com IA...'):
        resultados = leitor_texto.readtext(imagem, detail=0)
        numero_encontrado = None
        
        for texto in resultados:
            texto_limpo = texto.replace(" ", "")
            if re.fullmatch(r'\d{5,7}', texto_limpo):
                numero_encontrado = texto_limpo
                break
        
        # Marca que este arquivo já foi lido para não repetir se a página recarregar
        st.session_state.ultimo_arquivo_id = foto_arquivo.file_id
        
        if numero_encontrado:
            st.success(f"Patrimônio lido com sucesso: {numero_encontrado}")
            st.session_state.registros.append({
                'Categoria': categoria_selecionada.upper(), 
                'Patrimonio': numero_encontrado
            })
        else:
            st.error("Não foi possível identificar os números. Tente focar apenas na numeração da etiqueta.")

# Interface com Abas
aba1, aba2 = st.tabs(["📸 Usar Câmera Nativa / Galeria", "📷 Câmera do Navegador"])

with aba1:
    st.info("No celular, esta opção permite usar o auto-foco da câmera do Android.")
    foto_upload = st.file_uploader("Tire uma foto ou escolha da galeria", type=['png', 'jpg', 'jpeg'])
    if foto_upload is not None:
        processar_imagem(foto_upload)

with aba2:
    foto_web = st.camera_input("Tire uma foto pelo navegador")
    if foto_web is not None:
        processar_imagem(foto_web)

st.divider()

# --- FORMATAÇÃO DA TABELA ---
if st.session_state.registros:
    st.subheader("Itens Lidos nesta Sessão")
    
    df_registros = pd.DataFrame(st.session_state.registros)
    categorias_unicas = df_registros['Categoria'].unique()
    
    df_formatado = pd.DataFrame()
    
    for cat in categorias_unicas:
        valores = df_registros[df_registros['Categoria'] == cat]['Patrimonio'].reset_index(drop=True)
        df_formatado[cat] = valores
    
    df_exibicao = df_formatado.fillna("")
    
    st.dataframe(df_exibicao, width='stretch')
    
    csv = df_formatado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Planilha (CSV)",
        data=csv,
        file_name='patrimonio_escola.csv',
        mime='text/csv',
    )
else:
    st.write("Nenhum item lido ainda.")