import PyPDF2
import csv

import io
import numpy as np
import easyocr
import re
from transformers import pipeline
from PIL import Image
from PIL.ExifTags import TAGS

#--------------------------------------------------------
# Para função que gera hash de keys
#
# import streamlit_authenticator as stauth

#--------------------------------------------------------
# Para função que gera a signature key
#
# import secrets
import base64 # esta é usada para OUTRAS COISAS TAMBÉM, como converter arquivos armazenados em banco de dados como base64 para bytes

#--------------------------------------------------------
# Para função que imprime em pdf a partir de MarkDown
#
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate
from reportlab.lib.enums import TA_JUSTIFY

#---------------------------------------------------------
# Para função que imprime pdf a partir de HTML
# 
from xhtml2pdf import pisa

#---------------------------------------------------------
# Para converter texto em áudio
# 
from gtts import gTTS
import playsound

#---------------------------------------------------------
# Para testar as variáveis de ambiente
#
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path='ambiente.env')

#---------------------------------------------------------------------------------------------------------------
# Função que Converte MarkDown para PDF a partir de MarkDown
# 

# def gerar_signature_key():
#     chave_secreta_bytes = secrets.token_bytes(32) # gera 32 bytes de dados aleatórios
#     signature_key = base64.urlsafe_b64encode(chave_secreta_bytes).decode('utf-8')
#     return signature_key
    
#
# FIM: Função que Converte MarkDown para PDF
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Função que Converte MarkDown para PDF a partir de MarkDown
# 

# def gerar_hash(_key):
#     hash_gerado = stauth.Hasher.hash(_key)
#     return hash_gerado

#
# FIM: Função que Converte MarkDown para PDF
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Função que salva Texto em um arquivo txt
# 

def salvar_txt(_texto, _nome_arquivo):
    try:
        with open(_nome_arquivo, 'w', encoding='utf-8') as arquivo:
            arquivo.write(_texto)
        print(f"Texto Markdown salvo com sucesso em '{_nome_arquivo}'")
    except Exception as e:
        print(f"Erro ao salvar o arquivo '{_nome_arquivo}': {e}")

#---------------------------------------------------------------------------------------------------------------
# Função que Converte MarkDown para PDF a partir de MarkDown
# 
def pre_processar_texto_para_pdf(texto_markdown, limite_linha=100):
    """
    Pré-processa o texto markdown para inserir quebras de linha manuais em linhas longas.

    Args:
        texto_markdown (str): Texto markdown original.
        limite_linha (int): Número máximo de caracteres por linha antes de tentar quebrar.

    Returns:
        str: Texto markdown pré-processado com quebras de linha.
    """
    linhas_originais = texto_markdown.splitlines()
    linhas_pre_processadas = []

    for linha in linhas_originais:
        if len(linha) > limite_linha:
            linhas_quebradas = []
            linha_atual = ""
            palavras = linha.split() # Tenta quebrar por palavras primeiro
            for palavra in palavras:
                if len(linha_atual + palavra + " ") <= limite_linha:
                    linha_atual += palavra + " "
                else:
                    linhas_quebradas.append(linha_atual.strip())
                    linha_atual = palavra + " " # Começa nova linha com a palavra atual
            linhas_quebradas.append(linha_atual.strip()) # Adiciona a última linha
            linhas_pre_processadas.extend(linhas_quebradas) # Adiciona as linhas quebradas
        else:
            linhas_pre_processadas.append(linha) # Linhas curtas ficam como estão
    return "\n".join(linhas_pre_processadas) # Junta tudo de volta em um texto


def converter_markdown_para_pdf_2(texto_markdown, nome_arquivo_pdf="relatorio.pdf"):
    """Gera PDF, formatando listas corretamente com indentação e quebra de linha."""
    doc = SimpleDocTemplate(nome_arquivo_pdf, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Estilos de texto (leading, spaceAfter, justify)
    style_normal = styles['Normal']
    style_normal.leading = 16
    style_normal.spaceAfter = 12
    style_normal.alignment = TA_JUSTIFY

    style_heading2 = styles['Heading2']
    style_heading2.leading = 18
    style_heading2.spaceAfter = 18
    style_heading2.alignment = TA_JUSTIFY

    style_bold = styles['Normal']
    style_bold.fontName = 'Helvetica-Bold'
    style_bold.leading = 16
    style_bold.alignment = TA_JUSTIFY

    linhas_markdown = texto_markdown.splitlines()
    bloco_paragrafo = []

    for linha_markdown in linhas_markdown:
        linha = linha_markdown.strip()

        if not linha: # Linha vazia
            if bloco_paragrafo:
                texto_paragrafo = " ".join(bloco_paragrafo)
                p = Paragraph(texto_paragrafo, style_normal)
                story.append(p)
                story.append(Spacer(1, 0.2*inch))
                bloco_paragrafo = []

        elif linha.startswith("##"): # Títulos
            if bloco_paragrafo:
                texto_paragrafo = " ".join(bloco_paragrafo)
                p = Paragraph(texto_paragrafo, style_normal)
                story.append(p)
                story.append(Spacer(1, 0.2*inch))
                bloco_paragrafo = []

            titulo = linha[2:].strip()
            p_titulo = Paragraph(titulo, style_heading2)
            story.append(p_titulo)
            story.append(Spacer(1, 0.3*inch))

        elif linha.startswith("**"): # Negrito
            if bloco_paragrafo:
                texto_paragrafo = " ".join(bloco_paragrafo)
                p = Paragraph(texto_paragrafo, style_normal)
                story.append(p)
                story.append(Spacer(1, 0.2*inch))
                bloco_paragrafo = []

            partes = linha[2:].split(':', 1)
            if len(partes) == 2:
                label = partes[0].strip() + ":"
                valor = partes[1].strip()
                texto_formatado = f"<font name='Helvetica-Bold'>{label}</font> {valor}"
            else:
                texto_formatado = f"<font name='Helvetica-Bold'>{linha[2:].strip()}</font>"
            p_negrito = Paragraph(texto_formatado, style_normal)
            story.append(p_negrito)
            story.append(Spacer(1, 0.2*inch))

        elif linha.startswith("-") or linha.startswith("*"): # ***MODIFICAÇÃO IMPORTANTE: PROCESSAMENTO DE LISTAS COM INDENTAÇÃO***
            # Determinar o nível de indentação (contar espaços em branco no início da linha)
            indentation_level = 0
            original_linha = linha_markdown # Manter a linha original para contar a indentação
            linha = linha.lstrip() # Remover espaços em branco do início para processar o conteúdo
            indentation_level = len(original_linha) - len(linha) # Calcular nível de indentação

            item_lista = linha[1:].strip() # Remover o marcador de lista (- ou *) e espaços

            # Criar uma string de espaços para indentação (4 espaços por nível de indentação)
            indent_space = "    " * (indentation_level // 4) # Ajuste o número de espaços conforme necessário

            texto_formatado = f"{indent_space}- {item_lista}" # Adicionar indentação e marcador de lista

            p_lista = Paragraph(texto_formatado, style_normal)
            story.append(p_lista)
            story.append(Spacer(1, 0.1*inch)) # Espaço menor após itens de lista


        else: # Parágrafos normais
            bloco_paragrafo.append(linha)

    if bloco_paragrafo: # Processar o último bloco de parágrafo
        texto_paragrafo = " ".join(bloco_paragrafo)
        p = Paragraph(texto_paragrafo, style_normal)
        story.append(p)

    doc.build(story)
    return nome_arquivo_pdf

def converter_markdown_para_pdf(texto_markdown, nome_arquivo_pdf="relatorio.pdf"):
    """Gera PDF, formatando listas corretamente com indentação e quebra de linha."""
    doc = SimpleDocTemplate(nome_arquivo_pdf, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Estilos de texto (leading, spaceAfter, justify)
    style_normal = styles['Normal']
    style_normal.leading = 16
    style_normal.spaceAfter = 12
    style_normal.alignment = TA_JUSTIFY

    style_heading2 = styles['Heading2']
    style_heading2.leading = 18
    style_heading2.spaceAfter = 18
    style_heading2.alignment = TA_JUSTIFY

    style_bold = styles['Normal']
    style_bold.fontName = 'Helvetica-Bold'
    style_bold.leading = 16
    style_bold.alignment = TA_JUSTIFY

    linhas_markdown = texto_markdown.splitlines()
    bloco_paragrafo = []

    for linha_markdown in linhas_markdown:
        linha = linha_markdown.strip()

        if not linha: # Linha vazia
            if bloco_paragrafo:
                texto_paragrafo = " ".join(bloco_paragrafo)
                p = Paragraph(texto_paragrafo, style_normal)
                story.append(p)
                story.append(Spacer(1, 0.2*inch))
                bloco_paragrafo = []

        elif linha.startswith("##"): # Títulos
            if bloco_paragrafo:
                texto_paragrafo = " ".join(bloco_paragrafo)
                p = Paragraph(texto_paragrafo, style_normal)
                story.append(p)
                story.append(Spacer(1, 0.2*inch))
                bloco_paragrafo = []

            titulo = linha[2:].strip()
            p_titulo = Paragraph(titulo, style_heading2)
            story.append(p_titulo)
            story.append(Spacer(1, 0.3*inch))

        elif linha.startswith("**"): # Negrito
            if bloco_paragrafo:
                texto_paragrafo = " ".join(bloco_paragrafo)
                p = Paragraph(texto_paragrafo, style_normal)
                story.append(p)
                story.append(Spacer(1, 0.2*inch))
                bloco_paragrafo = []

            partes = linha[2:].split(':', 1)
            if len(partes) == 2:
                label = partes[0].strip() + ":"
                valor = partes[1].strip()
                texto_formatado = f"<font name='Helvetica-Bold'>{label}</font> {valor}"
            else:
                texto_formatado = f"<font name='Helvetica-Bold'>{linha[2:].strip()}</font>"
            p_negrito = Paragraph(texto_formatado, style_bold)
            story.append(p_negrito)
            story.append(Spacer(1, 0.2*inch))

        elif linha.startswith("-") or linha.startswith("*"): # ***MODIFICAÇÃO IMPORTANTE: PROCESSAMENTO DE LISTAS COM INDENTAÇÃO***
            # Determinar o nível de indentação (contar espaços em branco no início da linha)
            indentation_level = 0
            original_linha = linha_markdown # Manter a linha original para contar a indentação
            linha = linha.lstrip() # Remover espaços em branco do início para processar o conteúdo
            indentation_level = len(original_linha) - len(linha) # Calcular nível de indentação

            item_lista = linha[1:].strip() # Remover o marcador de lista (- ou *) e espaços

            # Criar uma string de espaços para indentação (4 espaços por nível de indentação)
            indent_space = "    " * (indentation_level // 4) # Ajuste o número de espaços conforme necessário

            texto_formatado = f"{indent_space}- {item_lista}" # Adicionar indentação e marcador de lista

            p_lista = Paragraph(texto_formatado, style_normal)
            story.append(p_lista)
            story.append(Spacer(1, 0.1*inch)) # Espaço menor após itens de lista


        else: # Parágrafos normais
            bloco_paragrafo.append(linha)

    if bloco_paragrafo: # Processar o último bloco de parágrafo
        texto_paragrafo = " ".join(bloco_paragrafo)
        p = Paragraph(texto_paragrafo, style_normal)
        story.append(p)

    doc.build(story)
    return nome_arquivo_pdf



#
# FIM: Função que Converte MarkDown para PDF
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que Converte MarkDown para HTML
#

def converter_texto_para_html(texto_markdown):
    """Converte texto no formato 'markdown' para HTML, suportando títulos, negrito inline e parágrafos."""
    linhas = texto_markdown.splitlines()
    html_output = "<html><body>\n"

    for linha in linhas:
        linha = linha.strip()

        if linha.startswith("##"):
            titulo = linha[2:].strip()
            # Formatar títulos (h2)
            html_output += f"<h2>{titulo}</h2>\n"
        elif linha: # Linha não vazia (pode conter texto normal ou negrito inline)
            # Processar negrito inline **texto** usando regex antes de envolver em <p>
            linha_com_negrito_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', linha)
            # Envolver o resto da linha (já com negrito formatado) em parágrafo (p)
            html_output += f"<p>{linha_com_negrito_html}</p>\n"

    html_output += "</body></html>"
    return html_output

#
# FIM Converte MarkDown para HTML
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função para extrair texto de uma imagem usando EasyOCR
#
def extrair_texto_de_imagem_sem_ia_EasyOCR(imagem_bytes):
    """
    Converte uma imagem em formato de bytes para texto sem usar IA,
    extraindo metadados, informações básicas e utilizando OCR com EasyOCR.

    Args:
        imagem_bytes: Os bytes da imagem.

    Returns:
        Um dicionário contendo informações sobre a imagem, como metadados,
        tamanho, formato e texto extraído (se houver).
    """

    try:
        imagem = Image.open(io.BytesIO(imagem_bytes))
    except Exception as e:
        return f"Erro ao abrir a imagem: {e}"

    informacoes_da_imagem = {}

    # Metadados EXIF
    metadados_exif = {}
    if hasattr(imagem, "_getexif"):
        exif = imagem._getexif()
        if exif is not None:
            for tag, valor in exif.items():
                nome_da_tag = TAGS.get(tag, tag)
                metadados_exif[nome_da_tag] = valor
    informacoes_da_imagem["metadados_exif"] = metadados_exif

    # Informações básicas
    informacoes_da_imagem["formato"] = imagem.format
    informacoes_da_imagem["tamanho"] = imagem.size
    informacoes_da_imagem["modo_de_cor"] = imagem.mode

    # Texto na imagem (OCR com EasyOCR)
    texto_extraido = ""
    try:
        leitor = easyocr.Reader(['pt', 'en'])  # 'pt' para português, 'en' para inglês
        imagem_np_array = np.array(imagem)
        resultado = leitor.readtext(imagem_np_array)
        # resultado = leitor.readtext(imagem)
        # texto_extraido = ""
        for (caixa_delimitadora, texto, confianca) in resultado:
            texto_extraido += texto + " "
        informacoes_da_imagem["texto_extraido"] = texto_extraido
    except Exception as e:
        informacoes_da_imagem["texto_extraido"] = f"Erro no OCR com EasyOCR: {e}"

    return texto_extraido
#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Função para extrair texto de uma imagem usanco OCR Pysseract
#
def extrair_texto_de_imagem_sem_ia(imagem_bytes):
    """
    Converte uma imagem em formato de bytes para texto sem usar IA,
    extraindo metadados, informações básicas e utilizando OCR para texto na imagem.

    Args:
        imagem_bytes: Os bytes da imagem.

    Returns:
        Um dicionário contendo informações sobre a imagem, como metadados,
        tamanho, formato e texto extraído (se houver).
    """

    try:
        imagem = Image.open(io.BytesIO(imagem_bytes))
    except Exception as e:
        return f"Erro ao abrir a imagem: {e}"

    informacoes_da_imagem = {}

    # Metadados EXIF
    metadados_exif = {}
    if hasattr(imagem, "_getexif"):
        exif = imagem._getexif()
        if exif is not None:
            for tag, valor in exif.items():
                nome_da_tag = TAGS.get(tag, tag)
                metadados_exif[nome_da_tag] = valor
    informacoes_da_imagem["metadados_exif"] = metadados_exif

    # Informações básicas
    informacoes_da_imagem["formato"] = imagem.format
    informacoes_da_imagem["tamanho"] = imagem.size
    informacoes_da_imagem["modo_de_cor"] = imagem.mode

    # Texto na imagem (OCR)
    try:
        import pytesseract  # Certifique-se de ter o pytesseract instalado
        texto_extraido = pytesseract.image_to_string(imagem)
        informacoes_da_imagem["texto_extraido"] = texto_extraido
    except ImportError:
        informacoes_da_imagem["texto_extraido"] = "Pytesseract não instalado."
    except Exception as e:
        informacoes_da_imagem["texto_extraido"] = f"Erro no OCR: {e}"

    return informacoes_da_imagem
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função para extrair texto de um PDF
#
def extrair_texto_de_imagem(imagem_base64):
    """
    Converte uma imagem em formato base64 para texto usando o modelo BLIP.

    Args:
        imagem_base64: Uma string contendo a imagem em formato base64.

    Returns:
        Uma string contendo a descrição textual da imagem.
    """

    # Decodifica a imagem base64 para dados binários
    imagem_binaria = base64.b64decode(imagem_base64)
    
    # Converte os dados binários para um objeto PIL
    imagem_pil = Image.open(io.BytesIO(imagem_binaria))

    # Cria um pipeline de image-to-text com o modelo BLIP
    gerador_de_legenda = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")

    # Gera a legenda da imagem
    descricao = gerador_de_legenda(imagem_pil)[0]["generated_text"]

    return descricao
#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Função para extrair texto de um PDF
#
def extrair_texto_de_pdf(pdf_path):
    if pdf_path == '':
        return ''
    else:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Função que armaezena em uma tabela a categorização dos chamados "NÃO CATEGORIZADOS" e "NÃO ATENDIDOS"
#
# Exemplo de uso converter_para_csv(nome_tabela, nome_arquivo, campos = ["Id_Ticket", "Resumo", "Dificuldade", "SLA"])
def converter_para_csv(tabela, nome_arquivo, fieldnames):
    """Converte a tabela para um arquivo CSV, sobrescrevendo o arquivo existente ou criando um novo."""
    with open(nome_arquivo, 'w', newline='') as arquivo_csv:  # Abre o arquivo em modo de escrita ('w')
        # Cria o cabeçalho do CSV
        #fieldnames = ["Id_Ticket", "Resumo", "Dificuldade", "SLA"]
        writer = csv.DictWriter(arquivo_csv, fieldnames=fieldnames, delimiter=';')

        writer.writeheader()

        # Escreve os dados na tabela
        for linha in tabela:
            writer.writerow(linha)
    pass

def converter_para_csv_v2(tabela, nome_arquivo, fieldnames):
    """Converte a tabela para um arquivo CSV, sobrescrevendo o arquivo existente ou criando um novo."""
    try:
        with open(nome_arquivo, 'w', encoding='utf-8', newline='') as arquivo_csv:
            writer = csv.DictWriter(arquivo_csv, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for linha in tabela:
                # Limpeza de caracteres problemáticos
                linha_limpa = {}
                for chave, valor in linha.items():
                    if isinstance(valor, str):
                        linha_limpa[chave] = valor.replace('\u200b', '')  # Remove espaços de largura zero
                    else:
                        linha_limpa[chave] = valor
                writer.writerow(linha_limpa)
    except Exception as e:
        print(f"Erro ao converter para CSV: {e}")
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que remove símbolos do texto. No momento, apenas '*' e '#'
#
def limpa_texto(_texto, _alvo, _transformacao):
    sujeira = True
    contador = 0
    while sujeira:
        if _alvo in _texto:
            _texto = _texto.replace(_alvo, _transformacao)
        else:
            sujeira = False
            contador += 1
    return _texto
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que imprime PDF a partir de HTML
# 
def converter_html_em_pdf_xhtml2pdf(html_string, nome_arquivo_pdf="relatorio_html.pdf"):
    """Gera PDF a partir de HTML usando xhtml2pdf (pisa)."""
    with open(nome_arquivo_pdf, "w+b") as pdf_file:
        pisa_status = pisa.CreatePDF(
            html_string,                # Conteúdo HTML
            dest=pdf_file)           # Arquivo para guardar o PDF

    # verificar o estado de erro
    if pisa_status.err:
        print(f"ERRO ao gerar PDF com xhtml2pdf: {pisa_status.err}")
        return None
    return nome_arquivo_pdf
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que converte TEXTO em FALA
# 
def texto_para_audio(texto, idioma='pt-br'): # Experimente mudar o idioma aqui
    tts = gTTS(texto, lang=idioma)
    arquivo_audio = "audio.mp3"
    tts.save(arquivo_audio)
    return arquivo_audio
    # playsound.playsound("audio.mp3")
    
def falar(arq_path):
    playsound.playsound(arq_path)
#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# START: TESTES
# 
