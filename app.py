import streamlit as st
import pandas as pd
import cv2
import numpy as np
import easyocr
import re

# Configuração da página
st.set_page_config(page_title="Scanner Escolar", layout="centered", page_icon="🏫")

# --- GERENCIAMENTO DE ESTADO (MEMÓRIA) ---
if 'registros' not in st.session_state:
    st.session_state.registros = []

if 'ultimo_arquivo_id' not in st.session_state:
    st.session_state.ultimo_arquivo_id = None

# Carrega a IA (Cache)
@st.cache_resource
def carregar_leitor():
    return easyocr.Reader(['pt', 'en'])

leitor_texto = carregar_leitor()

# --- CABEÇALHO E IDENTIFICAÇÃO DA SALA ---
st.title("🏫 Scanner de Patrimônio")

# Campo para ela digitar a sala antes de começar
nome_sala = st.text_input("Nome da Sala / Turma (Ex: Sala 3B, Cozinha):", placeholder="Digite o local aqui...")

if not nome_sala:
    st.warning("⚠️ Digite o nome da sala acima para liberar o scanner.")
    st.stop() # Para o app aqui até ela digitar o nome

st.write(f"📸 Registrando itens da: **{nome_sala}**")

# --- SELEÇÃO DE CATEGORIA ---
opcoes_categorias = ["Mesas", "Cadeiras", "Estantes", "Ar-Condicionado", "Informática", "Armários", "Nova Categoria..."]
escolha_categoria = st.selectbox("O que você vai escanear agora?", opcoes_categorias)

if escolha_categoria == "Nova Categoria...":
    categoria_selecionada = st.text_input("Digite o nome da categoria:")
else:
    categoria_selecionada = escolha_categoria

# --- FUNÇÃO DE PROCESSAMENTO ---
def processar_imagem(foto_arquivo):
    if not categoria_selecionada:
        st.error("Selecione ou digite uma categoria.")
        return
        
    # Evita processar a mesma foto duas vezes
    if st.session_state.ultimo_arquivo_id == foto_arquivo.file_id:
        return 

    # Lê a imagem
    file_bytes = np.asarray(bytearray(foto_arquivo.read()), dtype=np.uint8)
    imagem = cv2.imdecode(file_bytes, 1)
    
    with st.spinner('Lendo número...'):
        resultados = leitor_texto.readtext(imagem, detail=0)
        numero_encontrado = None
        
        # Procura números de 5 a 7 dígitos
        for texto in resultados:
            texto_limpo = texto.replace(" ", "").replace(".", "").replace("-", "")
            if re.search(r'\d{5,7}', texto_limpo):
                # Pega apenas a parte numérica se houver sujeira em volta
                match = re.search(r'\d{5,7}', texto_limpo)
                numero_encontrado = match.group()
                break
        
        st.session_state.ultimo_arquivo_id = foto_arquivo.file_id
        
        if numero_encontrado:
            st.toast(f"✅ {categoria_selecionada}: {numero_encontrado} adicionado!", icon="✅")
            st.session_state.registros.append({
                'Categoria': categoria_selecionada.upper(), 
                'Patrimonio': numero_encontrado
            })
        else:
            st.error("Não achei o número. Tente chegar mais perto.")

# --- ABAS DE CÂMERA ---
aba1, aba2 = st.tabs(["📱 Celular (Upload/Câmera)", "💻 Webcam"])

with aba1:
    st.caption("Se ao clicar abaixo não aparecer 'Câmera', verifique as permissões do navegador.")
    foto_upload = st.file_uploader("Tirar foto / Escolher Arquivo", type=['png', 'jpg', 'jpeg'], key="uploader")
    if foto_upload is not None:
        processar_imagem(foto_upload)

with aba2:
    foto_web = st.camera_input("Tirar foto agora")
    if foto_web is not None:
        processar_imagem(foto_web)

st.divider()

# --- EXIBIÇÃO E DOWNLOAD (CORREÇÃO DO ERRO DE TAMANHO) ---
if st.session_state.registros:
    st.subheader(f"Lista: {nome_sala}")
    
    # 1. Organiza os dados em listas separadas por categoria
    dados_organizados = {}
    for item in st.session_state.registros:
        cat = item['Categoria']
        pat = item['Patrimonio']
        if cat not in dados_organizados:
            dados_organizados[cat] = []
        dados_organizados[cat].append(pat)
    
    # 2. Descobre qual categoria tem mais itens (para nivelar a tabela)
    max_linhas = 0
    if dados_organizados:
        max_linhas = max(len(lista) for lista in dados_organizados.values())
    
    # 3. Preenche as listas menores com vazio "" para todas terem o mesmo tamanho
    for cat in dados_organizados:
        while len(dados_organizados[cat]) < max_linhas:
            dados_organizados[cat].append("")
            
    # 4. Cria o DataFrame quadrado perfeito
    df_final = pd.DataFrame(dados_organizados)
    
    # Mostra na tela
    st.dataframe(df_final, width=800)
    
    # Botão de Download
    nome_arquivo = f"Patrimonio_{nome_sala.replace(' ', '_')}.csv"
    csv = df_final.to_csv(index=False).encode('utf-8')
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.download_button(
            label=f"💾 Baixar Planilha da {nome_sala}",
            data=csv,
            file_name=nome_arquivo,
            mime='text/csv',
            type="primary"
        )
    with col2:
        if st.button("🗑️ Limpar Tudo"):
            st.session_state.registros = []
            st.rerun()

else:
    st.info("Nenhum item lido nesta sala ainda.")
