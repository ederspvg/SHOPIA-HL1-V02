import parametros_globais as OneRing
import streamlit as st
import pandas as pd
import re
import markdownify
import banco as Consulta_Banco
import send_email as Correio
import utilitarios as Canivete
import os
import time
import shutil
import tempfile
from rag import SistemaRAG  # Importa a classe do sistema RAG

# --- Inicialização do st.session_state ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if 'analise_aprofundada' not in st.session_state:
    st.session_state['analise_aprofundada'] = ''

if 'chamados_nao_categorizados' not in st.session_state:
    st.session_state['chamados_nao_categorizados'] = [pd.DataFrame(), '']

if 'audio_path' not in st.session_state:
    st.session_state['audio_path'] = ''

# --- Variável global para controlar a geração de áudio ---
if 'gerar_audio_global' not in st.session_state:
    st.session_state['gerar_audio_global'] = True

#-----------------------------------------------------------------------------------------------------
# FUNÇÃO PARA OBTER CHAMADOS NÃO CATEGORIZADOS
#
def obter_chamados_nao_categorizados():
    departamento = 1 # TI Sistemas = 1, TI Intraestrutura = 25, Fiscal = 10 
    dados = Consulta_Banco.listar_chamados_nao_categorizados('Open', '0000', '9999', departamento)
    retorno = [pd.DataFrame(dados[1]), dados[0]]
    return retorno

#-----------------------------------------------------------------------------------------------------
# CONFIGURAÇÃO DE LOGIN E SENHA A PARTIR DAS VARIÁVEIS DE AMBIENTE ---
# Versão simples. Futuramente melhorar para uma versão melhor
#

#-----------------------------------------------------------------------------------------------------
# Função para salvar o arquivo na pasta e processar o documento incrementalmente
#
def salvar_e_processar_arquivo(rag_sistema, arquivo):
    """
    Salva o arquivo enviado em biblioteca_geral/documentos_incrementais e o processa
    usando a função adicionar_documento_incremental do SistemaRAG.

    Args:
        rag_sistema (SistemaRAG): Uma instância do SistemaRAG.
        arquivo (UploadedFile): O arquivo enviado pelo usuário.

    Returns:
        bool: True se o arquivo foi salvo e processado com sucesso, False caso contrário.
    """
    pasta_destino = os.path.join(OneRing.PASTA_BIBLIOTECA, "documentos_incrementais")
    os.makedirs(pasta_destino, exist_ok=True)  # Cria o diretório se não existir

    try:
        caminho_arquivo = os.path.join(pasta_destino, arquivo.name)
        with open(caminho_arquivo, "wb") as f:
            f.write(arquivo.getbuffer())
        st.success(f"Arquivo '{arquivo.name}' salvo em '{pasta_destino}'")

        # Processar o arquivo incrementalmente
        sucesso_adicao = rag_sistema.adicionar_documento_incremental(caminho_arquivo)
        if sucesso_adicao:
            st.success(f"Documento '{arquivo.name}' processado e adicionado à base RAG.")
            return True
        else:
            st.error(f"Falha ao adicionar documento '{arquivo.name}' à base RAG.")
            return False

    except Exception as e:
        st.error(f"Erro ao salvar ou processar o arquivo '{arquivo.name}': {e}")
        return False
#
#-----------------------------------------------------------------------------------------------------

if OneRing.TESTE_LOCAL_:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='ambiente.env')
    LOGIN_CORRETO = os.getenv('LOGIN_DE_ACESSO')
    SENHA_CORRETA = os.getenv('SENHA_DE_ACESSO')
else:
    import streamlit as st
    LOGIN_CORRETO = st.secrets["LOGIN_DE_ACESSO"]
    SENHA_CORRETA = st.secrets["SENHA_DE_ACESSO"]

#----------------------------------------------------------------------------------------------------
# --- FUNÇÃO PARA ENVIAR A RESPOSTA POR E-MAIL ---
#
def enviar_resposta_por_email(texto_resposta, email_destinatario):
    corpo_mail = texto_resposta
    corpo_mail = Canivete.limpa_texto(corpo_mail, '```markdown', '')
    corpo_mail = Canivete.limpa_texto(corpo_mail, '```', '')
    corpo_mail_html = Canivete.converter_texto_para_html(corpo_mail)
    arquivos = [Canivete.converter_html_em_pdf_xhtml2pdf(corpo_mail_html)]

    # Geração de áudio condicional
    if st.session_state['gerar_audio_global']:
        with st.spinner('Aguarde... Gerando arquivo de áudio...'):
            texto_audio = corpo_mail
            texto_audio = Canivete.limpa_texto(texto_audio, '*', '')
            texto_audio = Canivete.limpa_texto(texto_audio, '**', '')
            texto_audio = Canivete.limpa_texto(texto_audio, '#', '')
            texto_audio = Canivete.limpa_texto(texto_audio, '##', '')
            audio_path = Canivete.texto_para_audio(texto_audio)
            if audio_path:
                arquivos.append(audio_path)
                st.session_state['audio_path'] = audio_path # Atualiza o caminho do áudio

    if Correio.enviar_email_gmail_smtp(email_destinatario, "Análise de Chamado com IA", corpo_mail_html, arquivos):
        st.success("Email enviado com sucesso!")
        if st.session_state['gerar_audio_global'] and st.session_state['audio_path']:
            if st.button("Reproduzir Áudio", key=f"botao_reproduzir_audio_{email_destinatario}"): # Chave única por email
                Canivete.falar(st.session_state['audio_path'])
    else:
        st.error("Falha ao enviar email. Verifique o console para mais detalhes.")

#----------------------------------------------------------------------------------------------------
# --- FORMULÁRIO DE LOGIN ---
#
if not st.session_state['autenticado']:
    with st.form("login_form"):
        st.subheader("Login de Acesso")
        login_usuario = st.text_input("Login")
        senha_usuario = st.text_input("Senha", type="password")
        botao_login = st.form_submit_button("Entrar")

        if botao_login:
            if login_usuario == LOGIN_CORRETO and senha_usuario == SENHA_CORRETA:
                st.session_state['autenticado'] = True
                st.success("Login bem-sucedido!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Credenciais incorretas. Tente novamente.")
else:
    # --- BOTÃO DE LOGOUT ---
    if st.sidebar.button("Logout"):
        st.session_state['autenticado'] = False
        st.rerun()

    # --- Coluna lateral para controle geral ---
    with st.sidebar:
        st.header("Controles Gerais")
        st.session_state['gerar_audio_global'] = st.checkbox("Gerar Áudio das Respostas?", value=True)

    # --- Título da aplicação
    st.title("Suporte Orientado Por Heurística Inteligente Artificial - Helpdesk Nível 1 - versão 001")
    st.subheader("Assistente Virtual Experimental Categorizador de Chamados")

    # --- ABAS DA APLICAÇÃO
    aba1, aba2, aba3 = st.tabs(["Listar Tickets Não Categorizados", "Análise Aprofundada de Ticket", "RAG Tools"])

    # --- Aba 1: Listar Tickets Não Categorizados (MODIFICADA) ---
    with aba1:
        st.header("Listar Tickets Não Categorizados")
        st.markdown("Clique no botão abaixo para listar os tickets que ainda não foram categorizados.")

        if st.button("Listar Tickets Não Categorizados", key="botao_listar_nao_categorizados"):
            with st.spinner('Aguarde... Buscando chamados não categorizados...'):
                st.session_state['chamados_nao_categorizados'] = obter_chamados_nao_categorizados()

            st.dataframe(st.session_state['chamados_nao_categorizados'][0])

            st.subheader("Relatório de Análise Geral")
            st.session_state['analise_aprofundada'] =  Canivete.limpa_texto(st.session_state['chamados_nao_categorizados'][1], '```markdown', '')
            st.session_state['analise_aprofundada'] =  Canivete.limpa_texto(st.session_state['chamados_nao_categorizados'][1], '```', '')
            Canivete.converter_markdown_para_pdf(st.session_state['chamados_nao_categorizados'][1])
            st.markdown(f'<div style="word-wrap: break-word;">{st.session_state["chamados_nao_categorizados"][1]}</div>')

        email_aba1 = st.text_input("Email", key="email_input_aba_1")

        if st.button("Enviar Categorização por Email", key="botao_enviar_email_aba_1"):
            corpo_mail_1 = st.session_state['chamados_nao_categorizados'][1]
            corpo_mail_1 = Canivete.limpa_texto(corpo_mail_1, '```markdown', '')
            corpo_mail_1 = Canivete.limpa_texto(corpo_mail_1, '```', '')
            corpo_mail_1_html = Canivete.converter_texto_para_html(corpo_mail_1)
            arquivos_aba1 = [Canivete.converter_html_em_pdf_xhtml2pdf(corpo_mail_1_html), "lista_de_tickets_nao_categorizados.csv"]
            if Correio.enviar_email_gmail_smtp(email_aba1, "Categorização de Chamados com IA - Ordem de Priorização", corpo_mail_1_html, arquivos_aba1):
                st.write("Email enviado com sucesso!")
            else:
                st.write("Falha ao enviar email. Verifique o console para mais detalhes.")

    # --- Aba 2: Análise Aprofundada de Ticket (MODIFICADA) ---
    with aba2:
        st.header("Análise Aprofundada de Ticket")
        st.markdown("Selecione o tipo de ticket e insira o ID do ticket desejado para análise detalhada.")

        # --- SELETOR DE TIPO DE TICKET ADICIONADO ---
        tipo_ticket_analise = st.radio(
            "Tipo de Ticket para Análise:",
            ["Não Categorizados", "Já Categorizados"],
            key="tipo_ticket_radio"  # Chave única para o radio button
        )

        ticket_alvo = st.text_input("Ticket Alvo", key="ticket_alvo_input")

        if st.button("Análise Aprofundada", key="botao_analise_aprofundada"):
            ticket_alvo_val = st.session_state['ticket_alvo_input']
            tipo_analise_selecionada = st.session_state['tipo_ticket_radio']  # Obtém a escolha do radio button

            with st.spinner(f'Aguarde... Analisando ticket {ticket_alvo_val}...'):
                if tipo_analise_selecionada == "Não Categorizados":
                    # SE FOR "NÃO CATEGORIZADOS", CHAMA analise_profunda_ticket_nao_categorizados
                    departamento = 1 # TI Sistemas = 1, TI Intraestrutura = 25, Fiscal = 10
                    st.session_state['analise_aprofundada'] = Consulta_Banco.analise_profunda_ticket_nao_categorizados('Open', ticket_alvo_val, ticket_alvo_val, departamento)
                elif tipo_analise_selecionada == "Já Categorizados":
                    # SE FOR "JÁ CATEGORIZADOS", CHAMA analise_profunda_tickets_categorizados
                    # *** IMPORTANTE: ASSUMINDO QUE A FUNÇÃO 'analise_profunda_tickets_categorizados' EXISTE EM banco.py ***
                    st.session_state['analise_aprofundada'] = Consulta_Banco.analise_profunda_tickets_categorizados('Open', ticket_alvo_val, ticket_alvo_val)
                # BLOCO 'else' REMOVIDO - DESNECESSÁRIO COM st.radio

            # --- Restante do código para exibir e enviar email ---
            st.session_state['analise_aprofundada'] =  Canivete.limpa_texto(st.session_state['analise_aprofundada'], '```markdown', '')
            st.session_state['analise_aprofundada'] =   Canivete.limpa_texto(st.session_state['analise_aprofundada'], '```', '')
            Canivete.converter_markdown_para_pdf(st.session_state['analise_aprofundada'])
            st.markdown(f'<div style="word-wrap: break-word;">{st.session_state["analise_aprofundada"]}</div>')

        email_aba2 = st.text_input("Email", key="email_input_aba_2")

        if st.button("Enviar por Email", key="botao_enviar_email_aba_2"):
            if st.session_state['analise_aprofundada']:
                enviar_resposta_por_email(st.session_state['analise_aprofundada'], email_aba2)
            else:
                st.warning("Nenhuma análise para enviar por e-mail.")

    # --- Aba 3: Controle do RAG (MODIFICADA) ---
    with aba3:
        with st.container():
            st.header("Ferramentas RAG (Base de Conhecimento)")

            # Instancia o sistema RAG para obter informações e realizar ações
            # É instanciado aqui para podermos mostrar o status e usá-lo nos botões
            # Pode recarregar o modelo a cada interação, dependendo do cache do Streamlit. [cite: 20, 21, 22]
            try:
                rag_system = SistemaRAG(diretorio_persistencia=OneRing.PASTA_BANCO)
                st.info(f"Coleções RAG rastreadas atualmente: {len(rag_system.lista_nomes_colecoes)}")
                # Verifica se o diretório de persistência e o arquivo de lista existem
                if not os.path.exists(rag_system.diretorio_persistencia):
                    st.warning(f"Diretório de persistência '{rag_system.diretorio_persistencia}' não encontrado.")
                # if not rag_system.lista_nomes_colecoes and os.path.exists(LISTA_COLECOES_FILE):
                #     st.warning("Arquivo de lista de coleções encontrado, mas a lista está vazia ou não pôde ser carregada.")
                # elif not rag_system.lista_nomes_colecoes and not os.path.exists(LISTA_COLECOES_FILE):
                #     st.info("Nenhuma base RAG criada ainda. Use o upload e o botão 'Criar/Recriar Base'.")

            except Exception as e:
                st.error(f"Erro ao inicializar o Sistema RAG: {e}")
                st.stop() # Interrompe a execução da aba se o RAG não puder ser inicializado

            st.markdown("---") # Separador visual

            # --- Seção de Gerenciamento da Base ---
            st.subheader("1. Gerenciar Base de Conhecimento")

            # --- Upload de Arquivos ---
            st.markdown("**Adicionar Novos Documentos:**")
            uploaded_files = st.file_uploader(
                "Selecione arquivos (.pdf, .txt, .docx) para adicionar à pasta da biblioteca:",
                type=["pdf", "txt", "docx"],
                accept_multiple_files=True,
                key="rag_file_uploader" # Chave única
            )

            # Processa uploads imediatamente para que estejam prontos para a criação/recriação
            if uploaded_files:
                arquivos_salvos = 0
                pasta_destino = OneRing.PASTA_BIBLIOTECA
                os.makedirs(pasta_destino, exist_ok=True) # Garante que a pasta exista
                for uploaded_file in uploaded_files:
                    try:
                        caminho_arquivo = os.path.join(pasta_destino, uploaded_file.name)
                        with open(caminho_arquivo, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"Arquivo '{uploaded_file.name}' salvo em '{pasta_destino}'")
                        arquivos_salvos += 1
                    except Exception as e:
                        st.error(f"Erro ao salvar '{uploaded_file.name}': {e}")
                if arquivos_salvos > 0:
                    st.info("Os arquivos foram adicionados. Para incluí-los na base RAG, clique em 'Criar/Recriar Base'.")

            st.markdown("**Ações na Base:**")
            col1_rag, col2_rag = st.columns(2)

            with col1_rag:
                # --- Botão Criar/Recriar ---
                if st.button("🚀 Criar / Recriar Base", key="rag_create_button", help="Limpa a base anterior e processa TODOS os arquivos da pasta da biblioteca."):
                    with st.spinner(f"Recriando base RAG a partir de '{OneRing.PASTA_BIBLIOTECA}'... Isso pode levar alguns minutos."):
                        try:
                            # A função criar_colecoes já faz a limpeza antes
                            sucesso = rag_system.criar_colecoes(pasta_documentos=OneRing.PASTA_BIBLIOTECA)
                            if sucesso:
                                st.success(f"Base RAG recriada com sucesso! {len(rag_system.lista_nomes_colecoes)} coleções ativas.")
                                st.rerun() # Recarrega a página para atualizar o status
                            else:
                                st.error("Falha ao recriar a base RAG. Verifique os logs no console.")
                        except Exception as e:
                            st.error(f"Erro durante a criação/recriação da base: {e}")

            with col2_rag:
                # --- Botão Zerar ---
                st.markdown('<span style="color:yellow">Atenção: Zerar apaga toda a base de conhecimento RAG.</span>', unsafe_allow_html=True)
                if st.button("🗑️ Zerar TODA a Base", key="rag_delete_button", help="Apaga permanentemente todas as coleções RAG."):
                    # Adiciona uma confirmação extra
                    if 'confirmar_zerar' not in st.session_state:
                        st.session_state.confirmar_zerar = False

                    st.session_state.confirmar_zerar = st.checkbox("Confirmo que desejo apagar TODA a base RAG permanentemente.", key="rag_confirm_delete_cb")

                    if st.session_state.confirmar_zerar:
                        with st.spinner("Zerando todas as coleções RAG..."):
                            try:
                                sucesso = rag_system.zerar_todas_colecoes()
                                if sucesso:
                                    st.success("Base RAG zerada com sucesso!")
                                    st.session_state.confirmar_zerar = False # Reseta a confirmação
                                    st.rerun() # Recarrega a página para atualizar o status
                                else:
                                    st.error("Falha ao zerar a base RAG. Verifique os logs no console.")
                            except Exception as e:
                                st.error(f"Erro ao zerar a base: {e}")
                    else:
                        st.warning("Por favor, marque a caixa de confirmação para zerar a base.")

            st.markdown("---") # Separador visual

            # --- Seção de Adicionar Documento Incremental ---
            st.subheader("2. Adicionar Documento Incremental")

            # --- Upload de Arquivo Incremental ---
            uploaded_file_incremental = st.file_uploader(
                "Selecione um arquivo (.pdf, .txt, .docx) para adicionar à base de conhecimento:",
                type=["pdf", "txt", "docx"],
                key="rag_file_uploader_incremental"  # Chave única
            )

            if st.button("Adicionar Documento", key="rag_add_document_button"):
                if uploaded_file_incremental:
                    try:
                        # Cria um arquivo temporário
                        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file_incremental.name) as temp_file:
                            # Escreve o conteúdo do UploadedFile no arquivo temporário
                            temp_file.write(uploaded_file_incremental.getvalue())
                        
                        # Adiciona o documento à base de conhecimento usando o caminho do arquivo temporário
                        rag_system.adicionar_documento_incremental(temp_file.name)
                        st.success("Documento adicionado à base de conhecimento com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao adicionar documento: {e}")
                    finally:
                        # Garante que o arquivo temporário seja removido, mesmo em caso de erro
                        if temp_file:
                            os.remove(temp_file.name)
                else:
                    st.warning("Por favor, selecione um arquivo para adicionar.")

            st.markdown("---")  # Separador visual

            # --- Seção de Consulta ao RAG ---
            st.subheader("3. Consultar Base de Conhecimento")

            pergunta = st.text_area("Pergunta:", height=100, key="rag_pergunta")
            instrucao = st.text_area("Instrução para a IA (opcional):", value="Responda de forma clara e concisa, baseando-se estritamente no contexto fornecido.", height=80, key="rag_instrucao")

            # --- Configurações da Consulta ---
            st.markdown("**Configurações da Consulta:**")
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)

            with col_cfg1:
                # Combobox de modelos (mantido como no seu exemplo original)
                MODELOS_RAG = {
                    "Gemini 1.5 Flash": "gemini-1.5-flash", # Modelo recomendado
                    "Gemini 2.0 Flash Thinking Exp": "gemini-2.0-flash-thinking-exp",
                    "Gemini 2.0 Flash": "gemini-2.0-flash",
                    "Gemini 2.0 Flash EXP": "gemini-2.0-flash-exp",
                    "Gemini 2.5 Pro Exp-03-25": "gemini-2.5-pro-exp-03-25",
                    "Gemini 2.5 Flash Preview": "gemini-2.5-flash-preview-04-17",
                    # Adicione outros modelos se desejar testar
                    # "Gemini Pro": "gemini-pro",
                    # "Outro Modelo": "nome-do-modelo"
                }
                # Use apenas os nomes amigáveis no selectbox
                modelo_display = st.selectbox(
                    "Modelo Gemini:",
                    list(MODELOS_RAG.keys()),
                    key="rag_modelo_select"
                )
                # Obtém o nome técnico do modelo selecionado
                modelo_tecnico = MODELOS_RAG[modelo_display]

            with col_cfg2:
                # Input para n_results_per_colecao
                n_results_cfg = st.number_input(
                    "Resultados Iniciais/Doc:",
                    min_value=1,
                    value=5, # Valor padrão sugerido
                    step=1,
                    key="rag_n_results",
                    help="Número de chunks a recuperar inicialmente de CADA documento antes de filtrar."
                )

            with col_cfg3:
                # Input para max_distance_threshold
                max_dist_cfg = st.number_input(
                    "Limiar Máx. Distância:",
                    min_value=0.1,
                    max_value=2.0, # Distância Cosseno pode ir até ~1.41 ou 2
                    value=0.8, # Valor padrão que funcionou bem para você
                    step=0.05,
                    format="%.2f",
                    key="rag_max_dist",
                    help="Filtro de relevância (Métrica Cosseno). Menor = Mais similar. Ajuste entre 0.5 (muito estrito) e 1.2 (mais permissivo). Padrão: 0.8"
                )

            st.markdown("**Contexto Adicional (Opcional):**")
            col_up1, col_up2 = st.columns(2)
            with col_up1:
                pdf_upload = st.file_uploader("Anexar PDF à consulta", type=["pdf"], key="rag_pdf_consulta")
            with col_up2:
                imagem_upload = st.file_uploader("Anexar Imagem à consulta", type=["jpg", "png", "jpeg"], key="rag_img_consulta")

            st.markdown("---") # Separador visual

            # --- Botão de Consulta ---
            if st.button("Consultar RAG", key="rag_processar_consulta_button"):
                if not pergunta:
                    st.warning("Por favor, digite uma pergunta.")
                elif not rag_system.lista_nomes_colecoes:
                    st.error("Não há coleções RAG para consultar. Crie a base primeiro.")
                else:
                    pdf_path_temp = ""
                    imagem_path_temp = ""
                    try:
                        # Salva arquivos temporários se houver uploads para a consulta
                        if pdf_upload:
                            temp_dir = "temp_rag_uploads" # Pasta temporária
                            os.makedirs(temp_dir, exist_ok=True)
                            pdf_path_temp = os.path.join(temp_dir, pdf_upload.name)
                            with open(pdf_path_temp, "wb") as f:
                                f.write(pdf_upload.getbuffer())
                            print(f"DEBUG: PDF temporário salvo em {pdf_path_temp}") # Debug

                        if imagem_upload:
                            temp_dir = "temp_rag_uploads" # Pasta temporária
                            os.makedirs(temp_dir, exist_ok=True)
                            imagem_path_temp = os.path.join(temp_dir, imagem_upload.name)
                            with open(imagem_path_temp, "wb") as f:
                                f.write(imagem_upload.getbuffer())
                            print(f"DEBUG: Imagem temporária salva em {imagem_path_temp}") # Debug

                        # Executa a consulta com os parâmetros da UI
                        with st.spinner("Consultando a base RAG e gerando resposta..."):
                            resposta_rag = rag_system.consultar_multiplas_colecoes(
                                pergunta=pergunta,
                                instrucao=instrucao,
                                pdf_path=pdf_path_temp,
                                imagem_path=imagem_path_temp,
                                modelo_de_pensamento=modelo_tecnico, # Usa o nome técnico do modelo
                                n_results_per_colecao=n_results_cfg, # Usa o valor do number_input
                                max_distance_threshold=max_dist_cfg  # Usa o valor do number_input
                            )
                        st.markdown("---")
                        st.subheader("Resposta:")
                        st.markdown(resposta_rag) # Usa markdown para melhor formatação da resposta

                        email_aba3 = st.text_input("Email", key="email_input_aba_3")
                        if st.button("Enviar por Email", key="botao_enviar_email_aba_3"):
                            enviar_resposta_por_email(resposta_rag, email_aba3)

                    except Exception as e:
                        st.error(f"Erro durante a consulta RAG: {e}")
                        # Adicionar traceback para depuração mais profunda, se necessário
                        # import traceback
                        # st.code(traceback.format_exc())
                    finally:
                        # Remove arquivos temporários DEPOIS de tentar a consulta
                        if pdf_path_temp and os.path.exists(pdf_path_temp):
                            try:
                                os.remove(pdf_path_temp)
                                print(f"DEBUG: PDF temporário removido: {pdf_path_temp}") # Debug
                                # Tenta remover o diretório se estiver vazio
                                if os.path.exists("temp_rag_uploads") and not os.listdir("temp_rag_uploads"):
                                    os.rmdir("temp_rag_uploads")
                            except Exception as del_e:
                                print(f"Erro ao remover PDF temp: {del_e}") # Log erro remoção

                        if imagem_path_temp and os.path.exists(imagem_path_temp):
                            try:
                                os.remove(imagem_path_temp)
                                print(f"DEBUG: Imagem temporária removida: {imagem_path_temp}") # Debug
                                # Tenta remover o diretório se estiver vazio
                                if os.path.exists("temp_rag_uploads") and not os.listdir("temp_rag_uploads"):
                                    os.rmdir("temp_rag_uploads")
                            except Exception as del_e:
                                print(f"Erro ao remover Imagem temp: {del_e}") # Log erro remoção
                                