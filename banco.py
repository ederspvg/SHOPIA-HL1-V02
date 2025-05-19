import parametros_globais as OneRing
import psycopg2

import base64
from PIL import Image
import io
import os

import chromadb
from rag import SistemaRAG  # Importa a classe do sistema RAG

from PyPDF2 import PdfReader
import pandas as pd

import ia_gemini as brain
#import ia_gemini_2 as brain_2
import prompts_ia as Persona
import utilitarios as Canivete
import send_email as Correio
import markdownify

#--------------------------------------------
# Define se vai trabalhar local ou no cloud
ambiente_local = OneRing.TESTE_LOCAL_ # False

if ambiente_local:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='ambiente.env')

    key_host_banco  = os.getenv('KEY_BANCO_HOST')
    key_database    = os.getenv('KEY_BANCO_DATABASE')
    key_user        = os.getenv('KEY_BANCO_USER')
    key_pass        = os.getenv('KEY_BANCO_PASS')
    porta           = 5432
else:
    import streamlit as st
    key_host_banco  = st.secrets["KEY_BANCO_HOST"]
    key_database    = st.secrets["KEY_BANCO_DATABASE"]
    key_user        = st.secrets["KEY_BANCO_USER"] 
    key_pass        = st.secrets["KEY_BANCO_PASS"] 
    porta           = 7007

#---------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------
# Função que conecta no banco do Sensr e retorna o resultado de uma query em uma tabela
#
def consulta_sensr(_l_mostra,_query):
    # Configurações de conexão
    conn = psycopg2.connect(
        host=key_host_banco,
        database=key_database,
        user=key_user,
        password=key_pass,
        port=porta
    )
    # Crie um cursor
    cur = conn.cursor()
    
    # Consultar Tabela
    cur.execute(_query)
    resultado = cur.fetchall()
    
    # Obter o número de colunas
    num_colunas = len(cur.description)
    print(f"/n Número de colunas: {num_colunas}")
    
    # Lista o resultado dentro da função?
    if _l_mostra:
        print("RESULTADO DA CONSULTA:")
        for linha in resultado:
            # print(linha[0])
            print(linha)
            
    # Finaliza o cursor
    if conn:
            cur.close()
            conn.close()
    return resultado


#---------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------
# Função que conecta no banco do Sensr e retorna o resultado de uma query em uma tabela
# CHAMADOS ABERTOS
# 
def consulta_chamados_abertos(STATUS_, TICKET_START, TICKET_END):

    #---------------------
    # CONSTANTES
    #
    # TICKET
    EMAIL_USUARIO       = 0
    SLA_TICKET          = 1
    NOME_USER           = 2
    EMPRESA_USER        = 3
    CATEGORIA           = 4
    SERVICO             = 5
    TAREFA              = 6
    DEPARTAMENTO_USER   = 7
    GRUPO_TECNICO       = 8
    TECNICO             = 9
    DATA_SLA            = 10
    INFO                = 11
    DATA_UP             = 12
    DATA_CAD            = 13
    STATUS              = 14
    DESCRICAO_TICKET    = 15
    TITULO              = 16
    TICKET              = 17
    PHONE               = 18
    RAMAL               = 19
    CIDADE              = 20
    UF                  = 21
    PAIS                = 22
    TICKET_REAL         = 23
    # ANEXOS 
    POS_ARQUIVO_TIPO  = 0
    POS_ARQUIVO_BLOB  = 1
    
    #---------------------
    # Variaveis
    # 
    descricao_anexos = ''
    dados_do_chamado = ''
    
    # Query para buscar os Tickets Abertos no Sensr
    # CHAMADOS ABERTOS
    query_tickets = f'''
    select tb_tickets.email_user,tb_tickets.sla_task,tb_tickets.id_user_name,tb_tickets.company_name,tb_tickets.category_name,tb_tickets.catalog_service_name,tb_tickets.catalog_task_name,tb_tickets.department_name,tb_tickets.group_tech_name,tb_tickets.user_cad_name,tb_tickets.sla,tb_tickets.notes,tb_tickets.dt_up,tb_tickets.dt_cad,tb_tickets.status,tb_tickets.description,tb_tickets.subject,tb_tickets.id_tickets,tb_person.phone,tb_person.ramal,tb_city.name,tb_state.name,tb_country.name,tb_tickets.real_id,tb_tickets.group_tech_name
    from tb_tickets
    LEFT JOIN tb_user ON tb_user.id_user = fk_id_user
    LEFT JOIN tb_person ON tb_person.id_person = tb_user.fk_id_person
    LEFT JOIN tb_city ON tb_city.id_city = tb_user.id_city
    LEFT JOIN tb_state ON tb_state.id_state = tb_user.id_state
    LEFT JOIN tb_country ON tb_country.id_country = tb_user.id_country
    where tb_tickets.status = '{str(STATUS_)}'
    and tb_tickets.id_tickets >= '{str(TICKET_START)}'
    and tb_tickets.id_tickets <= '{str(TICKET_END)}'
    order by tb_tickets.id_tickets
    '''
    #res = consulta_sensr(False,"select email_user,sla_task,id_user_name,company_name,category_name,catalog_service_name,catalog_task_name,department_name,group_tech_name,user_cad_name,sla,notes,dt_up,dt_cad,status,description,subject,id_tickets from tb_tickets where status = 'Open' Order By id_tickets ")
    res = consulta_sensr(False, query_tickets)
    #print("CONSULTA TICKETS ABERTOS:")
    # Varre o resultado da query, ticket por ticket
    for linha in res:
        
        # Obtem os dados do chamado para análise
        dados_do_chamado = 'Dados do Chamado: '
        dados_do_chamado += "\n" + " Email do Usuário: " + linha[EMAIL_USUARIO]
        dados_do_chamado += "\n" +  " SLA do Ticket: " + str(linha[SLA_TICKET])
        dados_do_chamado += "\n" +  " Nome do Usuário: " + linha[NOME_USER]
        dados_do_chamado += "\n" +  " Empresa do Usuário: " + linha[EMPRESA_USER]
        dados_do_chamado += "\n" +  " Categoria do Ticket: " + linha[CATEGORIA]
        dados_do_chamado += "\n" +  " Serviço ao qual o Ticket se refere: " + linha[SERVICO]
        dados_do_chamado += "\n" +  " Tarefa a qual o Ticket se refere: " + linha[TAREFA]
        dados_do_chamado += "\n" +  " Departamento do Usuário: " + linha[DEPARTAMENTO_USER]
        dados_do_chamado += "\n" +  " Grupo Técnico ao qual o Ticket se destina: " + linha[GRUPO_TECNICO]
        dados_do_chamado += "\n" +  " Técnico alocado, caso haja: " + linha[TECNICO]
        dados_do_chamado += "\n" +  " Data do SLA do Ticket: " + linha[DATA_SLA]
        #dados_do_chamado += "\n" +  " Informações do Ticket: " + linha[INFO]
        if len(linha[INFO]) > 300:
            info_truncada = linha[INFO][:300] + "..."
        else:
            info_truncada = linha[INFO]
        dados_do_chamado += "\n" + " Informações do Ticket: " + info_truncada
        dados_do_chamado += "\n" +  " Data Up do Ticket: " + str(linha[DATA_UP])
        dados_do_chamado += "\n" +  " Data Cad do Ticket: " + str(linha[DATA_CAD])
        dados_do_chamado += "\n" +  " Status do Ticket: " + linha[STATUS]
        #dados_do_chamado += "\n" +  " Descrição do Ticket: " + linha[DESCRICAO_TICKET]
        if len(linha[DESCRICAO_TICKET]) > 100:
            info_truncada = linha[DESCRICAO_TICKET][:100] + "..."
        else:
            info_truncada = linha[DESCRICAO_TICKET]
        dados_do_chamado += "\n" +  " Descrição do Ticket: " + info_truncada
        
        dados_do_chamado += "\n" +  " Título do Ticket: " + linha[TITULO]
        dados_do_chamado += "\n" +  " Código do Ticket no Sistema de Helpdesk: " + str(linha[TICKET])
        dados_do_chamado += "\n" +  " Código Real do Ticket no Sistema de Helpdesl: " + str(linha[TICKET_REAL])
        dados_do_chamado += "\n" +  " Telefone do Usuário: " + str(linha[PHONE])
        dados_do_chamado += "\n" +  " Ramal do Usuário: " + str(linha[RAMAL])
        dados_do_chamado += "\n" +  " Cidade do Usuário: " + str(linha[CIDADE])
        dados_do_chamado += "\n" +  " UF do Usuário: " + str(linha[UF])
        dados_do_chamado += "\n" +  " País do Usuário: " + str(linha[PAIS])

        
        #print(linha[EMAIL_USUARIO] )
        #print(linha[TICKET] )
        
        # Query para buscar os anexos do Ticket no Sensr
        #query_file_ref = " Select tb_attach_global.namefile,tb_attach_global.blob From tb_tickets_file LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_tickets_file.id_tickets_file and tb_attach_global.type = 'ticket' Where tb_tickets_file.fk_id_tickets = '" + str(linha[TICKET]) + "' Order By tb_attach_global.namefile "
        # CHAMADOS ABERTOS
        query_file_ref = f'''
        SELECT
            COALESCE(tb_attach_global.namefile, '') AS namefile,
            COALESCE(tb_attach_global.blob, '') AS blob
        from tb_tickets_file
        LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_tickets_file.id_tickets_file and tb_attach_global.type = 'ticket'
        where tb_tickets_file.fk_id_tickets = {str(linha[TICKET])}
        order by tb_attach_global.namefile
        '''
    
        res_file_ref = consulta_sensr(False, query_file_ref)
        contador_anexo = 0
        descricao_anexos = ""
        for linha_file_ref in res_file_ref:
            contador_anexo += 1
            
            #print(linha_file_ref[POS_ARQUIVO_TIPO])
            #print(linha_file_ref[POS_ARQUIVO_BLOB])
            
            if linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".jpg"):
                # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
                blob_data = linha_file_ref[1]
                
                # Decodificar o Base64
                image_data = base64.b64decode(blob_data)
                
                # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                image = Image.open(io.BytesIO(image_data))
                
                # Salva a imagem em um arquivo (ou exibe, se preferir)
                image.save("imagem_temporaria.jpg")  # Salva como PNG. Você pode ajustar o formato.
                
                # Ou, para exibir a imagem:
                image.show()
                
                #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                image_path  = "imagem_temporaria.jpg"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
                #print(f'Descrição: {descricao_anexos}')
                
            elif linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".png"):
                # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
                blob_data = linha_file_ref[1]
                
                # Decodificar o Base64
                image_data = base64.b64decode(blob_data)
                
                # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                image = Image.open(io.BytesIO(image_data))
                
                # Salva a imagem em um arquivo (ou exibe, se preferir)
                image.save("imagem_temporaria.png")  # Salva como PNG. Você pode ajustar o formato.
                
                # Ou, para exibir a imagem:
                image.show()
                
                #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                image_path  = "imagem_temporaria.png"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
                #print(f'Descrição: {descricao_anexos}')
                
            elif linha_file_ref[0].lower().endswith(".pdf"):
                # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
                blob_data = linha_file_ref[POS_ARQUIVO_BLOB]
                
                # Decodifica o Base4
                pdf_data = base64.b64decode(blob_data)
                
                # Cria um "arquivo em memória" com os dados do PDF
                pdf_file = io.BytesIO(pdf_data)
                
                # Salva o arquivo PDF
                with open("arquivo_temporario.pdf", "wb") as f:
                    f.write(pdf_file.getvalue())
                    
                # Abrir o arquivo PDF com visualizador padrão
                os.startfile("arquivo_temporario.pdf") # para o Windows
                # Ou:
                # os.system("open arquivo.pdf") # Para macOS ou Linux
                
                # Ler informações do PDF (opicional)
                pdf_reader = PdfReader(pdf_file)
                num_paginas = len(pdf_reader.pages)
                #print(f"Número de páginas: {num_paginas}")
                
                #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                arquivo_path  = "arquivo_temporario.pdf"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
                #print(f'Descrição: {descricao_anexos}')
                
            else:
                print("tipo de arquivo do anexo não previsto")
                pass
        #######################################
        # Chama a IA para analisar o chamado   
        # 
        analise_ia  = ''
        question    = ''
        _instrucao  = ''
        
        _instrucao  = Persona.biblioteca_de_prompts(Persona.BIBLIOTECARIO_)
        question    = "por favor analise as informações detalhadas do Ticket e a descrição dos anexos (caso haja algum anexo) e faça uma análise técnica preliminar conforme suas instruções ditam e responda indicando qual manual é mais indicado para orientar o analista que cuidará do caso."
        question    += "\n" + " DESCRIÇÃO DOS ANEXOS: " + descricao_anexos + "\n" + " DADOS DO CHAMADO: " + dados_do_chamado
        
        manual_indicado = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        
        question    = "por favor, analise a descrição dos anexos (caso haja algum anexo) e as informações detalhadas do Ticket e faça uma análise técnica conforme suas instruções ditam."
        question    += "\n" + " DESCRIÇÃO DOS ANEXOS: " + descricao_anexos + "\n" + " DADOS DO CHAMADO: " + dados_do_chamado
        _instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_COMPLETO_2_)
        #_instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_)
        
        arquivo_path  = manual_indicado # 'manuais/sigacom.pdf' # "protheus_custom/Lutms097.pdf"
        texto_do_manual = Canivete.extrair_texto_de_pdf(arquivo_path)
        
        question += "\n" + "Manual em Texto: \n" + texto_do_manual
        
        analise_ia  = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
        # analise_ia  = brain.limpa_texto(analise_ia)
        analise_ia  = "Analise IA: \n " + analise_ia
        resultado_final = "DADOS DO CHAMADO: "  + "\n" + dados_do_chamado  + "\n" + "RESULTADO FINAL DA ANÁLISE AUTOMÁTICA:" + "\n" + "ANEXOS:" + "\n" + descricao_anexos + "\n" + "ANALISE FEITA POR IA:" + "\n" + analise_ia
        #print(f'Descrição: {resultado_final}') 
        print(resultado_final)
        
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que conecta no banco do Sensr e retorna o resultado de uma query em uma tabela
# CHAMADOS NÃO CATEGORIZADOS
#
def consulta_chamados_nao_categorizados(STATUS_, TICKET_START, TICKET_END):

    #---------------------
    # CONSTANTES
    #
    # TICKET
    ID_                     = 0
    ASSUNTO_                = 1
    DESC_                   = 2
    CIDADE_                 = 3
    UF_                     = 4
    PAIS_                   = 5
    TELEFONE_               = 6
    RAMAL_                  = 7
    MAIL_                   = 8
    CATEGORIA_              = 9
    SERVICO_                = 10
    TAREFA_                 = 11
    DEPARTAMENTO_           = 12
    EMPRESA_                = 13
    SLA_TAREFA_             = 14
    COMPLEXIDADE_TAREFA_    = 15
    DATA_TICKET_            = 16
    NOME_USUARIO_           = 17


    # ANEXOS 
    POS_ARQUIVO_TIPO  = 0
    POS_ARQUIVO_BLOB  = 1
    
    #---------------------
    # Variaveis
    # 
    descricao_anexos = ''
    dados_do_chamado = ''
    tabela_categorizacao = []
    
    # Query para buscar os Tickets Abertos no Sensr
    # CHAMADOS NÃO CATEGORIZADOS
    query_tickets = f'''
    SELECT
        tb_request.id_request AS ID,
        COALESCE(tb_request.subject, '') AS ASSUNTO,
        COALESCE(tb_request.description, '') AS DESC,
        COALESCE(tb_city.name, '') AS CIDADE,
        COALESCE(tb_state.name, '') AS UF,
        COALESCE(tb_country.name, '') AS PAIS,
        COALESCE(tb_person.phone, '') AS TELEFONE,
        COALESCE(tb_person.ramal, '') AS RAMAL_USER,
        COALESCE(tb_person.email, '') AS MAIL,
        COALESCE(tb_category.name, '') AS CATEGORIA,
        COALESCE(tb_catalog_service.name, '') AS SERVICO,
        COALESCE(tb_catalog_task.name, '') AS TAREFA,
        COALESCE(tb_department.name, '') AS DEPARTAMENTO,
        COALESCE(EMPRESA.name, '') AS EMPRESA_USER,
        COALESCE(tb_catalog_task.time_sla, 0) AS SLA_TAREFA,
        COALESCE(tb_catalog_task.complexity, '') AS COMPLEXIDADE_TAREFA,
        tb_request.dt_cad AS DATA_INPUT,
        tb_person.name as NOME,
        
    FROM tb_request
    LEFT JOIN tb_tickets ON tb_tickets.fk_id_request = tb_request.id_request
    LEFT JOIN tb_user ON tb_user.id_user = tb_request.user_cad::integer
    LEFT JOIN tb_person ON tb_person.id_person = tb_user.fk_id_person
    LEFT JOIN tb_city ON tb_city.id_city = tb_user.id_city
    LEFT JOIN tb_state ON tb_state.id_state = tb_user.id_state
    LEFT JOIN tb_country ON tb_country.id_country = tb_user.id_country
    LEFT JOIN tb_category ON tb_category.id_category = tb_request.fk_id_category
    LEFT JOIN tb_catalog_service ON tb_catalog_service.id_catalog_service = tb_request.fk_id_catalog_service
    LEFT JOIN tb_catalog_task ON tb_catalog_task.id_catalog_task = tb_request.fk_id_catalog_task
    LEFT JOIN tb_department ON tb_department.id_department = tb_user.fk_id_department
    LEFT JOIN tb_company ON tb_company.id_company = tb_request.fk_id_company
    LEFT JOIN tb_person AS EMPRESA ON EMPRESA.id_person = tb_company.fk_id_person
    WHERE
        tb_request.status = '{str(STATUS_)}'
        AND tb_request.id_request >= '{str(TICKET_START)}'
        AND tb_request.id_request <= '{str(TICKET_END)}'
    ORDER BY tb_request.id_request
    '''
    #res = consulta_sensr(False,"select email_user,sla_task,id_user_name,company_name,category_name,catalog_service_name,catalog_task_name,department_name,group_tech_name,user_cad_name,sla,notes,dt_up,dt_cad,status,description,subject,id_tickets from tb_tickets where status = 'Open' Order By id_tickets ")
    res = consulta_sensr(False, query_tickets)
    #print("CONSULTA TICKETS ABERTOS:")
    # Varre o resultado da query, ticket por ticket
    for linha in res:
        
        # Obtem os dados do chamado para análise
        dados_do_chamado = 'Dados do Chamado: '
        dados_do_chamado +=  "\n" + " ID da Requisição: " + str(linha[ID_])
        dados_do_chamado +=  "\n" + " Data do Ticket: " + str(linha[DATA_TICKET_])
        dados_do_chamado +=  "\n" + " Assunto da Requisição: " + linha[ASSUNTO_]
        dados_do_chamado +=  "\n" + " Descrição da Requisição: " + linha[DESC_]
        dados_do_chamado +=  "\n" + " Cidade do Usuário: " + linha[CIDADE_]
        dados_do_chamado +=  "\n" + " UF do Usuário: " + linha[UF_]
        dados_do_chamado +=  "\n" + " País do Usuário: " + linha[PAIS_]
        dados_do_chamado +=  "\n" + " Telefone do Usuário: " + linha[TELEFONE_]
        dados_do_chamado +=  "\n" + " Ramal do Usuário: " + linha[RAMAL_]
        dados_do_chamado +=  "\n" + " Email do Usuário: " + linha[MAIL_]
        dados_do_chamado +=  "\n" + " Categoria da Requisição: " + linha[CATEGORIA_]
        dados_do_chamado +=  "\n" + " Serviço da Requisição: " + linha[SERVICO_]
        dados_do_chamado +=  "\n" + " Tarefa da Requisição: " + linha[TAREFA_]
        dados_do_chamado +=  "\n" + " SLA da Tarefa: " + str(linha[SLA_TAREFA_])
        dados_do_chamado +=  "\n" + " Complexidade da Tarefa: " + linha[COMPLEXIDADE_TAREFA_]
        dados_do_chamado +=  "\n" + " Departamento do Usuário: " + linha[DEPARTAMENTO_]
        dados_do_chamado +=  "\n" + " Empresa do Usuário: " + linha[EMPRESA_]
        dados_do_chamado +=  "\n" + " Nome do Usuário: " + linha[NOME_USUARIO_]
        
        #print(linha[EMAIL_USUARIO] )
        #print(linha[TICKET] )
        
        # Query para buscar os anexos do Ticket no Sensr
        # CHAMADOS NÃO CATEGORIZADOS
        #
        query_file_ref = f'''
        SELECT
            COALESCE(tb_attach_global.namefile, '') AS namefile,
            COALESCE(tb_attach_global.blob, '') AS blob
        FROM tb_request_file
        LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_request_file.id_request_file AND tb_attach_global.type = 'request'
        WHERE tb_request_file.fk_id_request = {str(linha[ID_])}
        ORDER BY tb_attach_global.namefile
        '''
    
        res_file_ref = consulta_sensr(False, query_file_ref)
        contador_anexo = 0
        descricao_anexos = ""
        l_descricao_img_com_Gemini = False
        l_descricao_pdf_com_Gemini = False
        for linha_file_ref in res_file_ref:
            contador_anexo += 1
            
            #print(linha_file_ref[POS_ARQUIVO_TIPO])
            #print(linha_file_ref[POS_ARQUIVO_BLOB])
            
            if linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".jpg"):
                # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
                blob_data = linha_file_ref[1]
                
                #-----------------------------------------------------------------------------------
                # Obter a descrição da imagem via transform para econimizar consultas a API GEMINI
                # STATUS: desabilitado, pois a descrição gerada é pobre em detalhes
                #
                # descricao_imagem_exp = Canivete.extrair_texto_de_imagem(blob_data)
                # print(" \n Descrição da Imagem: \n " + descricao_imagem_exp + " \n ")
                
                # Decodificar o Base64
                image_data = base64.b64decode(blob_data)
                
                if l_descricao_img_com_Gemini:
                    # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                    image = Image.open(io.BytesIO(image_data))
                    # Salva a imagem em um arquivo (ou exibe, se preferir)
                    image.save("imagem_temporaria.jpg")  # Salva como PNG. Você pode ajustar o formato.
                    # Ou, para exibir a imagem:
                    # Usado apenas para teste do funcionamento da conversão do arquivo
                    # image.show()
                    
                    #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                    _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                    image_path  = "imagem_temporaria.jpg"
                    descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                else:
                    #-----------------------------------------------------------------------------------
                    # Obter a descrição da imagem via biblioteca EasyOCR (sem uso de IA) para
                    # economizar consultas à API Gemini, reservando-as para analisar o contexto geral
                    #
                    descricao_imagem_ocr = Canivete.extrair_texto_de_imagem_sem_ia_EasyOCR(image_data)
                    print(" \n Descrição da Imagem: \n " + descricao_imagem_ocr + " \n ")
                    descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: " + descricao_imagem_ocr
                #print(f'Descrição: {descricao_anexos}')
                
            elif linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".png"):
                # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
                blob_data = linha_file_ref[1]
                
                # Decodificar o Base64
                image_data = base64.b64decode(blob_data)
                
                if l_descricao_img_com_Gemini:
                    # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                    image = Image.open(io.BytesIO(image_data))
                    # Salva a imagem em um arquivo (ou exibe, se preferir)
                    image.save("imagem_temporaria.png")  # Salva como PNG. Você pode ajustar o formato.
                    # Ou, para exibir a imagem:
                    # Usado apenas para testar a conversão do arquivo
                    # image.show()
                    #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                    _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                    image_path  = "imagem_temporaria.png"
                    descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                else:
                    #-----------------------------------------------------------------------------------
                    # Obter a descrição da imagem via biblioteca EasyOCR (sem uso de IA) para
                    # economizar consultas à API Gemini, reservando-as para analisar o contexto geral
                    #
                    descricao_imagem_ocr = Canivete.extrair_texto_de_imagem_sem_ia_EasyOCR(image_data)
                    print(" \n Descrição da Imagem: \n " + descricao_imagem_ocr + " \n ")
                    descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: " + descricao_imagem_ocr
                #print(f'Descrição: {descricao_anexos}')    
            elif linha_file_ref[0].lower().endswith(".pdf"):
                # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
                blob_data = linha_file_ref[POS_ARQUIVO_BLOB]
                
                # Decodifica o Base4
                pdf_data = base64.b64decode(blob_data)
                
                # Cria um "arquivo em memória" com os dados do PDF
                pdf_file = io.BytesIO(pdf_data)
                
                # Salva o arquivo PDF
                with open("arquivo_temporario.pdf", "wb") as f:
                    f.write(pdf_file.getvalue())
                
                if l_descricao_pdf_com_Gemini:
                    #-------------------------------------------------------
                    # Abrir o arquivo PDF com visualizador padrão
                    # Usado apenas para testar a conversão do arquivo
                    # os.startfile("arquivo_temporario.pdf") # para o Windows
                    # Ou:
                    # os.system("open arquivo.pdf") # Para macOS ou Linux
                    
                    #-------------------------------------------------------
                    # Ler informações do PDF (opicional)
                    #
                    pdf_reader = PdfReader(pdf_file)
                    num_paginas = len(pdf_reader.pages)
                    #print(f"Número de páginas: {num_paginas}")
                    #-------------------------------------------------------
                    # Obter informações do arquivo com Gemini
                    #
                    _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                    arquivo_path  = "arquivo_temporario.pdf"
                    descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos += brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                else:
                    arquivo_path = "arquivo_temporario.pdf"
                    descricao_anexos += Canivete.extrair_texto_de_pdf(arquivo_path)
                    
                #print(f'Descrição: {descricao_anexos}')
                
            else:
                print("tipo de arquivo do anexo não previsto")
                pass
        #######################################
        # Chama a IA para analisar o chamado   
        # 
        analise_ia  = ''
        question    = ''
        _instrucao  = ''
        
        _instrucao  = Persona.biblioteca_de_prompts(Persona.BIBLIOTECARIO_)
        question    = "por favor analise as informações detalhadas do Ticket e a descrição dos anexos (caso haja algum anexo) e faça uma análise técnica preliminar conforme suas instruções ditam e responda indicando qual manual é mais indicado para orientar o analista que cuidará do caso."
        question    += "\n" + " DESCRIÇÃO DOS ANEXOS: " + descricao_anexos + "\n" + " DADOS DO CHAMADO: " + dados_do_chamado
        
        manual_indicado = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        if '\n' in manual_indicado:
            manual_indicado = manual_indicado.replace('\n', '')
        
        question    = "por favor, analise a descrição dos anexos (caso haja algum anexo) e as informações detalhadas do Ticket e faça uma análise técnica conforme suas instruções ditam."
        question    += "\n" + " DESCRIÇÃO DOS ANEXOS: " + descricao_anexos + "\n" + " DADOS DO CHAMADO: " + dados_do_chamado
        _instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_COMPLETO_2_)
        #_instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_)
        
        arquivo_path  = manual_indicado # 'manuais/sigacom.pdf' # "protheus_custom/Lutms097.pdf"
        if manual_indicado == '#N/A':
            texto_do_manual = arquivo_path = ''
        else:
            texto_do_manual = Canivete.extrair_texto_de_pdf(arquivo_path)
        
        question += "\n" + "Manual em Texto: \n" + texto_do_manual
        
        analise_ia  = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
        # analise_ia  = brain.limpa_texto(analise_ia)
        analise_ia  = " \n Analise IA: \n " + analise_ia
        resultado_final = "DADOS DO CHAMADO: "  + "\n" + dados_do_chamado  + "\n" + "RESULTADO FINAL DA ANÁLISE AUTOMÁTICA:" + "\n" + "ANEXOS:" + "\n" + descricao_anexos + "\n" + "ANALISE FEITA POR IA:" + "\n" + analise_ia
        # print(resultado_final)
        print("DADOS DO CHAMADO: "  + "\n" + dados_do_chamado  + "\n" + "ANALISE FEITA POR IA:" + "\n" + analise_ia)
        
        #-------------------------------------------------------------------------------------
        # EXTRAIR ID da Requisição:
        #
        titulo      = 'DADOS_TICKET'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao campo {titulo} sem incluir o campo {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_ticket  = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR Assunto da Requisição:
        #
        titulo      = 'ASSUNTO'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao campo {titulo} sem incluir o campo {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_assunto  = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR CATEGORIZAÇÃO
        #
        titulo      = 'CATEGORIZACAO'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_categ   = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR TIPO DE REQUISIÇÃO
        #
        titulo      = 'TIPO_REQ'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_tipo_r  = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR GRAU DE DIFICULDADE
        #
        titulo      = 'DIFICULDADE'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_grau    = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR ORIENTAÇÕES PARA O ANALISTA HUMANO
        #
        titulo      = 'ORIENTACAO_H'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_human   = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR RESPOSTA INICIAL PARA O USUÁRIO
        #
        titulo      = 'RESPOSTA_INI'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_user    = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #-------------------------------------------------------------------------------------
        # EXTRAIR SLA SUGERIDO
        #
        titulo      = 'SLA_SUGERIDO'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_sla_s   = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        
        #-------------------------------------------------------------------------------------
        # EXTRAIR VENCIMENTO SLA ATUAL
        #
        titulo      = 'VENCIMENTO_SLA_ATUAL'
        _instrucao  = Persona.biblioteca_de_prompts(Persona.EXTRATOR_DE_DADOS_)
        question    = f'Leia o texto abaixo e extraia apenas o trecho referente ao título {titulo} sem incluir o título {titulo} na resposta: \n '
        question    = question + resultado_final
        tab_sla_a   = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        #tabela_categorizacao = []
        
        ticket_categorizado = {
            "Dados do Ticket": tab_ticket,
            "Assunto": tab_assunto,
            "Análise da Categorização": tab_categ,
            "Análise do Tipo da Requisição": tab_tipo_r,
            "Análise do Grau de Dificuldade": tab_grau,
            "Orientações para o Analista Humano": tab_human,
            "Resposta inicial para o Usuário": tab_user,
            "Análise do SLA": tab_sla_s,
            "Vencimento do SLA Atual": tab_sla_a,
        }
        tabela_categorizacao.append(ticket_categorizado)
        
        print(" \n FIM PARCIAL \n ")
    arq_csv     = 'tickets_nao_categorizados.csv'
    campos_csv  = ["Dados do Ticket", "Assunto", "Análise da Categorização", 
                   "Análise do Tipo da Requisição", "Análise do Grau de Dificuldade", 
                   "Orientações para o Analista Humano", "Resposta inicial para o Usuário",
                   "Análise do SLA", "Vencimento do SLA Atual"]
    Canivete.converter_para_csv_v2(tabela_categorizacao, arq_csv,campos_csv )
    print(" \n FIM \n ")
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que conecta no banco do Sensr e retorna o resultado de uma query em uma tabela
# CHAMADOS JÁ CATEGORIZADOS
#
def analise_profunda_tickets_categorizados(STATUS_, TICKET_START, TICKET_END):

    #---------------------
    # CONSTANTES
    #
    # TICKET
    ID_                     = 24
    ASSUNTO_                = 16
    DESC_                   = 15
    CIDADE_                 = 20
    UF_                     = 21
    PAIS_                   = 22
    TELEFONE_               = 18
    RAMAL_                  = 19
    MAIL_                   = 0
    CATEGORIA_              = 4
    SERVICO_                = 5
    TAREFA_                 = 6
    DEPARTAMENTO_           = 7
    EMPRESA_                = 3
    SLA_TAREFA_             = 1
    COMPLEXIDADE_TAREFA_    = 14
    DATA_TICKET_            = 15
    NOME_USER_              = 2
    ID_PARA_ANEXOS          = 25
    DEPTO_TECH_             = 26


    # ANEXOS 
    POS_ARQUIVO_TIPO  = 0
    POS_ARQUIVO_BLOB  = 1
    
    #---------------------
    # Variaveis
    # 
    descricao_anexos = ''
    dados_do_chamado = ''
    tabela_categorizacao = []
    
    # Query para buscar os Tickets Abertos no Sensr
    # CHAMADOS NÃO CATEGORIZADOS
    query_tickets = f'''
    select 
        COALESCE(tb_tickets.email_user, '') AS MAIL,
        tb_tickets.sla_task AS SLA_TAREFA,
        tb_tickets.id_user_name AS NOME,
        COALESCE(tb_tickets.company_name, '') AS EMPRESA_USER,
        COALESCE(tb_tickets.category_name, '') AS CATEGORIA,
        COALESCE(tb_tickets.catalog_service_name, '') AS SERVICO,
        COALESCE(tb_tickets.catalog_task_name, '') AS TAREFA,
        COALESCE(tb_tickets.department_name, '') AS DEPARTAMENTO,
        COALESCE(tb_tickets.group_tech_name, ''),
        COALESCE(tb_tickets.user_cad_name, ''),
        tb_tickets.sla AS SLA_DATA,
        COALESCE(tb_tickets.notes, ''),
        tb_tickets.dt_up,
        tb_tickets.dt_cad as DATA_INPUT,
        COALESCE(tb_tickets.status, ''),
        COALESCE(tb_tickets.description, '') AS DESC,
        COALESCE(tb_tickets.subject, '') AS ASSUNTO,
        tb_tickets.id_tickets AS ID_INTERNO,
        COALESCE(tb_person.phone, '') AS TELEFONE,
        COALESCE(tb_person.ramal, '') AS RAMAL_USER,
        COALESCE(tb_city.name, '') AS CIDADE,
        COALESCE(tb_state.name, '') AS UF,
        COALESCE(tb_country.name, '') AS PAIS,
        COALESCE(tb_catalog_task.complexity, '') AS COMPLEXIDADE_TAREFA,
        tb_tickets.real_id AS ID,
        tb_tickets.fk_id_request AS ID_ANEXO,
        tb_tickets.group_tech_name AS DEPTO_TECH
            from tb_tickets
            LEFT JOIN tb_user ON tb_user.id_user = fk_id_user
            LEFT JOIN tb_person ON tb_person.id_person = tb_user.fk_id_person
            LEFT JOIN tb_city ON tb_city.id_city = tb_user.id_city
            LEFT JOIN tb_state ON tb_state.id_state = tb_user.id_state
            LEFT JOIN tb_country ON tb_country.id_country = tb_user.id_country
            LEFT JOIN tb_catalog_task ON tb_catalog_task.id_catalog_task = tb_tickets.fk_id_catalog_task
            where 
            tb_tickets.real_id >= '{str(TICKET_START)}'
            and tb_tickets.real_id <= '{str(TICKET_END)}'
            order by tb_tickets.id_tickets
    '''
            # tb_tickets.status = '{str(STATUS_)}'
            # and tb_tickets.id_tickets >= '{str(TICKET_START)}'
            # and tb_tickets.id_tickets <= '{str(TICKET_END)}'
    #res = consulta_sensr(False,"select email_user,sla_task,id_user_name,company_name,category_name,catalog_service_name,catalog_task_name,department_name,group_tech_name,user_cad_name,sla,notes,dt_up,dt_cad,status,description,subject,id_tickets from tb_tickets where status = 'Open' Order By id_tickets ")
    res = consulta_sensr(False, query_tickets)
    #print("CONSULTA TICKETS ABERTOS:")
    # Varre o resultado da query, ticket por ticket
    for linha in res:
        
        # Obtem os dados do chamado para análise
        dados_do_chamado = 'Dados do Chamado: '
        dados_do_chamado +=  "\n" + " ID da Requisição: " + str(linha[ID_])
        dados_do_chamado +=  "\n" + " Data do Ticket: " + str(linha[DATA_TICKET_])
        dados_do_chamado +=  "\n" + " Assunto da Requisição: " + linha[ASSUNTO_]
        # dados_do_chamado +=  "\n" + " Descrição da Requisição: " + linha[DESC_]
        
        if len(linha[DESC_]) > 300:
            dados_do_chamado +=  "\n" + " Descrição da Requisição: " + linha[DESC_][:300] + "..."
        else:
            dados_do_chamado +=  "\n" + " Descrição da Requisição: " + linha[DESC_]
        
        dados_do_chamado +=  "\n" + " Cidade do Usuário: " + linha[CIDADE_]
        dados_do_chamado +=  "\n" + " UF do Usuário: " + linha[UF_]
        dados_do_chamado +=  "\n" + " País do Usuário: " + linha[PAIS_]
        dados_do_chamado +=  "\n" + " Telefone do Usuário: " + linha[TELEFONE_]
        dados_do_chamado +=  "\n" + " Ramal do Usuário: " + linha[RAMAL_]
        dados_do_chamado +=  "\n" + " Email do Usuário: " + linha[MAIL_]
        dados_do_chamado +=  "\n" + " Categoria da Requisição: " + linha[CATEGORIA_]
        dados_do_chamado +=  "\n" + " Serviço da Requisição: " + linha[SERVICO_]
        dados_do_chamado +=  "\n" + " Tarefa da Requisição: " + linha[TAREFA_]
        dados_do_chamado +=  "\n" + " SLA da Tarefa: " + str(linha[SLA_TAREFA_])
        dados_do_chamado +=  "\n" + " Complexidade da Tarefa: " + linha[COMPLEXIDADE_TAREFA_]
        dados_do_chamado +=  "\n" + " Departamento do Usuário: " + linha[DEPARTAMENTO_]
        dados_do_chamado +=  "\n" + " Empresa do Usuário: " + linha[EMPRESA_]
        dados_do_chamado +=  "\n" + " Nome do Usuário: " + linha[NOME_USER_]
        dados_do_chamado +=  "\n" + " Departamento Tecnico: " + str(linha[DEPTO_TECH_])
        
        
        #print(linha[EMAIL_USUARIO] )
        #print(linha[TICKET] )
        
        # Query para buscar os anexos do Ticket no Sensr
        # CHAMADOS NÃO CATEGORIZADOS
        #
        # query_file_ref = f'''
        # SELECT
        #     COALESCE(tb_attach_global.namefile, '') AS namefile,
        #     COALESCE(tb_attach_global.blob, '') AS blob
        # FROM tb_request_file
        # LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_request_file.id_request_file AND tb_attach_global.type = 'request'
        # WHERE tb_request_file.fk_id_request = {str(linha[ID_])}
        # ORDER BY tb_attach_global.namefile
        # '''

        #----------------------------------------------------------------------------
        # Buscar descrição dos anexos, caso haja
        #
        descricao_anexos = ""
        
        descricao_anexos = busca_descricao_anexos_tickets_categorizados(str(linha[ID_PARA_ANEXOS]))
        
        print("\n Descrição \n " + descricao_anexos + " \n ")
        
        #----------------------------------------------------------------------------
        # Chama a IA para analisar o chamado   
        # 
        analise_ia  = ''
        question    = ''
        _instrucao  = ''
        
        _instrucao  = Persona.biblioteca_de_prompts(Persona.BIBLIOTECARIO_)
        question    = "por favor analise as informações detalhadas do Ticket e a descrição dos anexos (caso haja algum anexo) e faça uma análise técnica preliminar conforme suas instruções ditam e responda indicando qual manual é mais indicado para orientar o analista que cuidará do caso."
        question    += "\n" + " DESCRIÇÃO DOS ANEXOS: " + descricao_anexos + "\n" + " DADOS DO CHAMADO: " + dados_do_chamado
        
        manual_indicado = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
        if '\n' in manual_indicado:
            manual_indicado = manual_indicado.replace('\n', '')
            
        arquivo_path  = manual_indicado # 'manuais/sigacom.pdf' # "protheus_custom/Lutms097.pdf"
        if manual_indicado == '#N/A':
            texto_do_manual = arquivo_path = ''
        else:
            texto_do_manual = Canivete.extrair_texto_de_pdf(arquivo_path)
        
        question    = f"""
                        Resolva o chamado a seguir: 
                        """
        
        question    = question + "\n" + " DESCRIÇÃO DOS ANEXOS: \n " + descricao_anexos + "\n" + " DADOS DO CHAMADO: \n " + dados_do_chamado
        
        _instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_2_)
        
        # arquivo_path  = manual_indicado # 'manuais/sigacom.pdf' # "protheus_custom/Lutms097.pdf"
        # if manual_indicado == '#N/A':
        #     texto_do_manual = arquivo_path = ''
        # else:
        #     texto_do_manual = Canivete.extrair_texto_de_pdf(arquivo_path)
        
        question += "\n" + "Manual em Texto: \n" + texto_do_manual
        arquivo_path = ''
        
        usa_rag = True
        
        if usa_rag:
            print(" \n USANDO RAG \n")
            #--------------------------------------------
            try:
                rag_system = SistemaRAG(diretorio_persistencia=OneRing.PASTA_BANCO)
                print(f"Coleções RAG rastreadas atualmente: {len(rag_system.lista_nomes_colecoes)}")
                if not os.path.exists(rag_system.diretorio_persistencia):
                    print(f"Diretório de persistência '{rag_system.diretorio_persistencia}' não encontrado.")
            except Exception as e:
                print(f"Erro ao inicializar o Sistema RAG: {e}")
                
            _instrucao = Persona.biblioteca_de_prompts(Persona.QUESTIONADOR_)
            pergunta   = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)

            analise_ia = rag_system.consultar_multiplas_colecoes(
                                    pergunta=pergunta,
                                    instrucao="Haja como um especialista nos assuntos questionados e responda de forma clara, detalhada e ao mesmo tempo didática.",
                                    # pdf_path="caminho/para/um/pdf_extra.pdf", # Exemplo
                                    # imagem_path="caminho/para/uma/imagem_extra.png", # Exemplo
                                    modelo_de_pensamento="gemini-2.0-flash-thinking-exp", # gemini-2.0-flash-thinking-exp # gemini-2.0-flash
                                    n_results_per_colecao=15, # Quantos chunks buscar por *cada* coleção/documento
                                    max_distance_threshold=0.8 # Limiar de distância máxima para filtrar os chunks recuperados
                                )
            question = question + "\n" + "BASE DE CONHECIMENTO: \n" + analise_ia
            # print(f" \n Pergunta Final: {question} \n ")
            _instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_2_)
            analise_ia  = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
        else:
            analise_ia  = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
            
        # analise_ia  = brain.limpa_texto(analise_ia)
        # analise_ia  = " \n Analise IA: \n " + analise_ia
        # resultado_final = "DADOS DO CHAMADO: "  + "\n" + dados_do_chamado  + "\n" + "RESULTADO FINAL DA ANÁLISE AUTOMÁTICA:" + "\n" + "ANEXOS:" + "\n" + descricao_anexos + "\n" + "ANALISE FEITA POR IA:" + "\n" + analise_ia
        
        
    return analise_ia
#
# FIM
#---------------------------------------------------------------------------------------------------------------





#---------------------------------------------------------------------------------------------------------------
# Função que conecta no banco do Sensr e retorna o resultado de uma query em uma tabela
# CHAMADOS NÃO CATEGORIZADOS
#
def analise_profunda_ticket_nao_categorizados(STATUS_, TICKET_START, TICKET_END, DEPARTAMENTO_TECNICO):
    print(" \n APTNC: PASSO 1 \n ")
    #---------------------
    # CONSTANTES
    #
    # TICKET
    ID_                     = 0
    ASSUNTO_                = 1
    DESC_                   = 2
    CIDADE_                 = 3
    UF_                     = 4
    PAIS_                   = 5
    TELEFONE_               = 6
    RAMAL_                  = 7
    MAIL_                   = 8
    CATEGORIA_              = 9
    SERVICO_                = 10
    TAREFA_                 = 11
    DEPARTAMENTO_           = 12
    EMPRESA_                = 13
    SLA_TAREFA_             = 14
    COMPLEXIDADE_TAREFA_    = 15
    DATA_TICKET_            = 16
    NOME_USER_              = 17
    DEPTO_TECH_             = 18
    

    # ANEXOS 
    POS_ARQUIVO_TIPO  = 0
    POS_ARQUIVO_BLOB  = 1
    
    #---------------------
    # Variaveis
    # 
    descricao_anexos = ''
    dados_do_chamado = ''
    tabela_categorizacao = []
    
    print(" \n APTNC: PASSO 2 \n ")
    
    # Query para buscar os Tickets Abertos no Sensr
    # CHAMADOS NÃO CATEGORIZADOS
    query_tickets = f'''
    SELECT
        tb_request.id_request AS ID,
        COALESCE(tb_request.subject, '') AS ASSUNTO,
        COALESCE(tb_request.description, '') AS DESC,
        COALESCE(tb_city.name, '') AS CIDADE,
        COALESCE(tb_state.name, '') AS UF,
        COALESCE(tb_country.name, '') AS PAIS,
        COALESCE(tb_person.phone, '') AS TELEFONE,
        COALESCE(tb_person.ramal, '') AS RAMAL_USER,
        COALESCE(tb_person.email, '') AS MAIL,
        COALESCE(tb_category.name, '') AS CATEGORIA,
        COALESCE(tb_catalog_service.name, '') AS SERVICO,
        COALESCE(tb_catalog_task.name, '') AS TAREFA,
        COALESCE(tb_department.name, '') AS DEPARTAMENTO,
        COALESCE(EMPRESA.name, '') AS EMPRESA_USER,
        COALESCE(tb_catalog_task.time_sla, 0) AS SLA_TAREFA,
        COALESCE(tb_catalog_task.complexity, '') AS COMPLEXIDADE_TAREFA,
        tb_request.dt_cad AS DATA_INPUT,
        tb_person.name as NOME,
        DEPTO_TECH.name
    FROM tb_request
    LEFT JOIN tb_tickets ON tb_tickets.fk_id_request = tb_request.id_request
    LEFT JOIN tb_user ON tb_user.id_user = tb_request.user_cad::integer
    LEFT JOIN tb_person ON tb_person.id_person = tb_user.fk_id_person
    LEFT JOIN tb_city ON tb_city.id_city = tb_user.id_city
    LEFT JOIN tb_state ON tb_state.id_state = tb_user.id_state
    LEFT JOIN tb_country ON tb_country.id_country = tb_user.id_country
    LEFT JOIN tb_category ON tb_category.id_category = tb_request.fk_id_category
    LEFT JOIN tb_catalog_service ON tb_catalog_service.id_catalog_service = tb_request.fk_id_catalog_service
    LEFT JOIN tb_catalog_task ON tb_catalog_task.id_catalog_task = tb_request.fk_id_catalog_task
    LEFT JOIN tb_department ON tb_department.id_department = tb_user.fk_id_department
    LEFT JOIN tb_company ON tb_company.id_company = tb_request.fk_id_company
    LEFT JOIN tb_person AS EMPRESA ON EMPRESA.id_person = tb_company.fk_id_person
    LEFT JOIN tb_department AS DEPTO_TECH ON DEPTO_TECH.id_department = tb_request.fk_id_department
    WHERE
        tb_request.status = '{str(STATUS_)}'
        AND tb_request.id_request >= '{str(TICKET_START)}'
        AND tb_request.id_request <= '{str(TICKET_END)}'
        AND tb_request.fk_id_department = '{str(DEPARTAMENTO_TECNICO)}'
    ORDER BY tb_request.id_request
    '''
    
    print(" \n APTNC: PASSO 3 \n ")
    #res = consulta_sensr(False,"select email_user,sla_task,id_user_name,company_name,category_name,catalog_service_name,catalog_task_name,department_name,group_tech_name,user_cad_name,sla,notes,dt_up,dt_cad,status,description,subject,id_tickets from tb_tickets where status = 'Open' Order By id_tickets ")
    res = consulta_sensr(False, query_tickets)
    #print("CONSULTA TICKETS ABERTOS:")
    
    analise_ia  = ''
    question    = ''
    _instrucao  = ''
    
    print(" \n APTNC: PASSO 4 \n ")
    
    # Varre o resultado da query, ticket por ticket
    for linha in res:
        print(" \n APTNC: PASSO 5 \n ")
        
        # Obtem os dados do chamado para análise
        dados_do_chamado = 'Dados do Chamado: '
        dados_do_chamado +=  "\n" + " ID da Requisição: " + str(linha[ID_])
        dados_do_chamado +=  "\n" + " Data do Ticket: " + str(linha[DATA_TICKET_])
        dados_do_chamado +=  "\n" + " Assunto da Requisição: " + linha[ASSUNTO_]
        dados_do_chamado +=  "\n" + " Descrição da Requisição: " + linha[DESC_]
        dados_do_chamado +=  "\n" + " Cidade do Usuário: " + linha[CIDADE_]
        dados_do_chamado +=  "\n" + " UF do Usuário: " + linha[UF_]
        dados_do_chamado +=  "\n" + " País do Usuário: " + linha[PAIS_]
        dados_do_chamado +=  "\n" + " Telefone do Usuário: " + linha[TELEFONE_]
        dados_do_chamado +=  "\n" + " Ramal do Usuário: " + linha[RAMAL_]
        dados_do_chamado +=  "\n" + " Email do Usuário: " + linha[MAIL_]
        dados_do_chamado +=  "\n" + " Categoria da Requisição: " + linha[CATEGORIA_]
        dados_do_chamado +=  "\n" + " Serviço da Requisição: " + linha[SERVICO_]
        dados_do_chamado +=  "\n" + " Tarefa da Requisição: " + linha[TAREFA_]
        dados_do_chamado +=  "\n" + " SLA da Tarefa: " + str(linha[SLA_TAREFA_])
        dados_do_chamado +=  "\n" + " Complexidade da Tarefa: " + linha[COMPLEXIDADE_TAREFA_]
        dados_do_chamado +=  "\n" + " Departamento do Usuário: " + linha[DEPARTAMENTO_]
        dados_do_chamado +=  "\n" + " Empresa do Usuário: " + linha[EMPRESA_]
        dados_do_chamado +=  "\n" + " Nome do Usuário: " + linha[NOME_USER_]
        dados_do_chamado +=  "\n" + " Departamento Tecnico: " + str(linha[DEPTO_TECH_])
        
        
        #print(linha[EMAIL_USUARIO] )
        #print(linha[TICKET] )
        
        # Query para buscar os anexos do Ticket no Sensr
        # CHAMADOS NÃO CATEGORIZADOS
        #
        # query_file_ref = f'''
        # SELECT
        #     COALESCE(tb_attach_global.namefile, '') AS namefile,
        #     COALESCE(tb_attach_global.blob, '') AS blob
        # FROM tb_request_file
        # LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_request_file.id_request_file AND tb_attach_global.type = 'request'
        # WHERE tb_request_file.fk_id_request = {str(linha[ID_])}
        # ORDER BY tb_attach_global.namefile
        # '''

        #----------------------------------------------------------------------------
        # Buscar descrição dos anexos, caso haja
        #
        descricao_anexos = ""
        
        descricao_anexos = busca_descricao_anexos_tickets(str(linha[ID_]))
        
        print("\n Descrição \n " + descricao_anexos + " \n ")
        
        #----------------------------------------------------------------------------
        # Chama a IA para analisar o chamado   
        # 
        analise_ia  = ''
        question    = ''
        _instrucao  = ''
        
        _instrucao  = Persona.biblioteca_de_prompts(Persona.BIBLIOTECARIO_)
        question    = "por favor analise as informações detalhadas do Ticket e a descrição dos anexos (caso haja algum anexo) e faça uma análise técnica preliminar conforme suas instruções ditam e responda indicando qual manual é mais indicado para orientar o analista que cuidará do caso."
        question    += "\n" + " DESCRIÇÃO DOS ANEXOS: " + descricao_anexos + "\n" + " DADOS DO CHAMADO: " + dados_do_chamado
        
        manual_indicado = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
        if '\n' in manual_indicado:
            manual_indicado = manual_indicado.replace('\n', '')
            
        arquivo_path  = manual_indicado # 'manuais/sigacom.pdf' # "protheus_custom/Lutms097.pdf"
        if manual_indicado == '#N/A':
            texto_do_manual = arquivo_path = ''
        else:
            texto_do_manual = Canivete.extrair_texto_de_pdf(arquivo_path)
        
        question    = f"""
                        Resolva o chamado a seguir: 
                        """
        
        question    = question + "\n" + " DESCRIÇÃO DOS ANEXOS: \n " + descricao_anexos + "\n" + " DADOS DO CHAMADO: \n " + dados_do_chamado
        
        _instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_2_)
        
        # arquivo_path  = manual_indicado # 'manuais/sigacom.pdf' # "protheus_custom/Lutms097.pdf"
        # if manual_indicado == '#N/A':
        #     texto_do_manual = arquivo_path = ''
        # else:
        #     texto_do_manual = Canivete.extrair_texto_de_pdf(arquivo_path)
        
        question += "\n" + "Manual em Texto: \n" + texto_do_manual
        arquivo_path = ''
        
        usa_rag = True
        
        if usa_rag:
            print(" \n USANDO RAG \n")
            #--------------------------------------------
            try:
                rag_system = SistemaRAG(diretorio_persistencia=OneRing.PASTA_BANCO)
                print(f"Coleções RAG rastreadas atualmente: {len(rag_system.lista_nomes_colecoes)}")
                if not os.path.exists(rag_system.diretorio_persistencia):
                    print(f"Diretório de persistência '{rag_system.diretorio_persistencia}' não encontrado.")
            except Exception as e:
                print(f"Erro ao inicializar o Sistema RAG: {e}")
                
            _instrucao = Persona.biblioteca_de_prompts(Persona.QUESTIONADOR_)
            pergunta   = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
            
            print(f" \n Pergunta: {pergunta} \n ")

            analise_ia = rag_system.consultar_multiplas_colecoes(
                                    pergunta=pergunta,
                                    instrucao="Haja como um especialista nos assuntos questionados e responda de forma clara, detalhada e ao mesmo tempo didática.",
                                    # pdf_path="caminho/para/um/pdf_extra.pdf", # Exemplo
                                    # imagem_path="caminho/para/uma/imagem_extra.png", # Exemplo
                                    modelo_de_pensamento= "gemini-2.0-flash-thinking-exp", #"gemini-2.0-flash"
                                    n_results_per_colecao=15, # Quantos chunks buscar por *cada* coleção/documento
                                    max_distance_threshold=0.8 # Limiar de distância máxima para filtrar os chunks recuperados
                                )
            question = question + "\n" + "BASE DE CONHECIMENTO: \n" + analise_ia
            # print(f" \n Pergunta Final: {question} \n ")
            _instrucao = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_2_)
            analise_ia  = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
        else:
            analise_ia  = brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_PESADO)
            
        # analise_ia  = brain.limpa_texto(analise_ia)
        # analise_ia  = " \n Analise IA: \n " + analise_ia
        # resultado_final = "DADOS DO CHAMADO: "  + "\n" + dados_do_chamado  + "\n" + "RESULTADO FINAL DA ANÁLISE AUTOMÁTICA:" + "\n" + "ANEXOS:" + "\n" + descricao_anexos + "\n" + "ANALISE FEITA POR IA:" + "\n" + analise_ia
        print(f" \n ANALISA IA: {analise_ia} \n ")
    print(" \n APTNC: PASSO 6 \n ")
    return analise_ia
#
# FIM
#---------------------------------------------------------------------------------------------------------------



#---------------------------------------------------------------------------------------------------------------
# Função que busca e retorna a descrição dos anexos de um ticket (tipos atuais: jpg, png e pdf)
#
def busca_descricao_anexos_tickets(_ticket_buscado):
    # ANEXOS 
    POS_ARQUIVO_TIPO  = 0
    POS_ARQUIVO_BLOB  = 1
    
    #---------------------
    # Variaveis
    # 
    descricao_anexos = ''
    # Query para buscar os anexos do Ticket no Sensr
    # CHAMADOS NÃO CATEGORIZADOS
    #
    query_file_ref = f'''
        SELECT
            COALESCE(tb_attach_global.namefile, '') AS namefile,
            COALESCE(tb_attach_global.blob, '') AS blob
        FROM tb_request_file
        LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_request_file.id_request_file AND tb_attach_global.type = 'request'
        WHERE tb_request_file.fk_id_request = {_ticket_buscado}
        ORDER BY tb_attach_global.namefile
        '''
    
    res_file_ref = consulta_sensr(False, query_file_ref)
    contador_anexo = 0
    descricao_anexos = ""
    l_descricao_img_com_Gemini = False
    l_descricao_pdf_com_Gemini = False
    l_usa_Gemini    = False
    for linha_file_ref in res_file_ref:
        contador_anexo += 1
        if linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".jpg"):
            #-------------------------------------------------------------------------------------------------------
            # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
            blob_data = linha_file_ref[1]
            #-----------------------------------------------------------------------------------
            # Obter a descrição da imagem via transform para econimizar consultas a API GEMINI
            # STATUS: desabilitado, pois a descrição gerada é pobre em detalhes
            #
            # descricao_imagem_exp = Canivete.extrair_texto_de_imagem(blob_data)
            # print(" \n Descrição da Imagem: \n " + descricao_imagem_exp + " \n ")
            #------------------------------------------------------------------------------------
            
            #-----------------------------------------------    
            # Decodificar o Base64
            #
            image_data = base64.b64decode(blob_data)
                
            if l_usa_Gemini:
                #----------------------------------------------------------------------------------------
                # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                image = Image.open(io.BytesIO(image_data))

                #----------------------------------------------------------------------------------------
                # Salva a imagem em um arquivo (ou exibe, se preferir)
                image.save("imagem_temporaria.jpg")  # Salva como PNG. Você pode ajustar o formato.
                # Ou, para exibir a imagem:
                # Usado apenas para teste do funcionamento da conversão do arquivo
                # image.show()
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                image_path  = "imagem_temporaria.jpg"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
            else:
                #-----------------------------------------------------------------------------------
                # Obter a descrição da imagem via biblioteca EasyOCR (sem uso de IA) para
                # economizar consultas à API Gemini, reservando-as para analisar o contexto geral
                #
                descricao_imagem_ocr = Canivete.extrair_texto_de_imagem_sem_ia_EasyOCR(image_data)
                print(" \n Descrição da Imagem: \n " + descricao_imagem_ocr + " \n ")
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: " + descricao_imagem_ocr
                
                if len(descricao_anexos) > 5000:
                    _instrucao = Persona.biblioteca_de_prompts(Persona.SINTETIZADOR_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica sem precisar ler desenas de páginas de error log."
                    question    = question + " Descrição do Anexo: \n " + str(contador_anexo) + " - descrição detalhada: "+ descricao_anexos
                    #arquivo_path  = "arquivo_temporario.pdf"
                    #descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                    
                    print(" \n Descrição Anexo - " + str(contador_anexo) +  " TAMANHO: " + str(len(descricao_anexos)) + " \n" + descricao_anexos)
                
        elif linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".png"):
            # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
            #
            blob_data = linha_file_ref[1]
            
            #------------------------------------------------    
            # Decodificar o Base64
            image_data = base64.b64decode(blob_data)
                
            if l_usa_Gemini:
                #---------------------------------------------------------------------------------------------
                # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                image = Image.open(io.BytesIO(image_data))
                #---------------------------------------------------------------------------------------------
                # Salva a imagem em um arquivo (ou exibe, se preferir)
                image.save("imagem_temporaria.png")  # Salva como PNG. Você pode ajustar o formato.
                # Ou, para exibir a imagem:
                # Usado apenas para testar a conversão do arquivo
                # image.show()
                #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                image_path  = "imagem_temporaria.png"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
            else:
                #-----------------------------------------------------------------------------------
                # Obter a descrição da imagem via biblioteca EasyOCR (sem uso de IA) para
                # economizar consultas à API Gemini, reservando-as para analisar o contexto geral
                #
                descricao_imagem_ocr = Canivete.extrair_texto_de_imagem_sem_ia_EasyOCR(image_data)
                print(" \n Descrição da Imagem: \n " + descricao_imagem_ocr + " \n ")
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: " + descricao_imagem_ocr
                
                if len(descricao_anexos) > 5000:
                    _instrucao = Persona.biblioteca_de_prompts(Persona.SINTETIZADOR_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica sem precisar ler desenas de páginas de error log."
                    question    = question + " Descrição do Anexo: \n " + str(contador_anexo) + " - descrição detalhada: "+ descricao_anexos
                    #arquivo_path  = "arquivo_temporario.pdf"
                    #descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                    
                    print(" \n Descrição Anexo - " + str(contador_anexo) +  " TAMANHO: " + str(len(descricao_anexos)) + " \n" + descricao_anexos)
            
               
        elif linha_file_ref[0].lower().endswith(".pdf"):
            #------------------------------------------------------------------------------------------------------
            # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
            blob_data = linha_file_ref[POS_ARQUIVO_BLOB]
            
            #-------------------------------------------------------    
            # Decodifica o Base4
            pdf_data = base64.b64decode(blob_data)
            #-------------------------------------------------------    
            # Cria um "arquivo em memória" com os dados do PDF
            pdf_file = io.BytesIO(pdf_data)
                
            # Salva o arquivo PDF
            with open("arquivo_temporario.pdf", "wb") as f:
                f.write(pdf_file.getvalue())
                
            if l_usa_Gemini:
                #-------------------------------------------------------
                # Abrir o arquivo PDF com visualizador padrão
                # Usado apenas para testar a conversão do arquivo
                # os.startfile("arquivo_temporario.pdf") # para o Windows
                # Ou:
                # os.system("open arquivo.pdf") # Para macOS ou Linux
                    
                #-------------------------------------------------------
                # Ler informações do PDF (opicional)
                #
                pdf_reader = PdfReader(pdf_file)
                num_paginas = len(pdf_reader.pages)
                #print(f"Número de páginas: {num_paginas}")
                #-------------------------------------------------------
                # Obter informações do arquivo com Gemini
                #
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                arquivo_path  = "arquivo_temporario.pdf"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
            else:
                arquivo_path = "arquivo_temporario.pdf"
                descricao_anexos += Canivete.extrair_texto_de_pdf(arquivo_path)
                
                if len(descricao_anexos) > 5000:
                    _instrucao = Persona.biblioteca_de_prompts(Persona.SINTETIZADOR_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica sem precisar ler desenas de páginas de error log."
                    question    = question + " Descrição do Anexo: \n " + str(contador_anexo) + " - descrição detalhada: "+ descricao_anexos
                    #arquivo_path  = "arquivo_temporario.pdf"
                    #descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                    
                    print(" \n Descrição Anexo - " + str(contador_anexo) +  " TAMANHO: " + str(len(descricao_anexos)) + " \n" + descricao_anexos)
        else:
            print("tipo de arquivo do anexo não previsto")
            pass
    print(" \n ANEXO - RESULTADO FINAL: \n " + descricao_anexos)
    return descricao_anexos
#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Função que busca e retorna a descrição dos anexos de um ticket (tipos atuais: jpg, png e pdf)
#
def busca_descricao_anexos_tickets_categorizados(_ticket_buscado):
    # ANEXOS 
    POS_ARQUIVO_TIPO  = 0
    POS_ARQUIVO_BLOB  = 1
    
    #---------------------
    # Variaveis
    # 
    descricao_anexos = ''
    # Query para buscar os anexos do Ticket no Sensr
    # CHAMADOS NÃO CATEGORIZADOS
    #
    query_file_ref = f'''
        
        select tb_attach_global.namefile,tb_attach_global.blob
        from tb_request_file
        LEFT JOIN tb_attach_global ON tb_attach_global.id_ref = tb_request_file.id_request_file and tb_attach_global.type = 'request'
        where tb_request_file.fk_id_request = {_ticket_buscado}
        order by tb_attach_global.namefile
        
        '''
    
    res_file_ref = consulta_sensr(False, query_file_ref)
    contador_anexo = 0
    descricao_anexos = ""
    l_descricao_img_com_Gemini = False
    l_descricao_pdf_com_Gemini = False
    l_usa_Gemini    = False
    for linha_file_ref in res_file_ref:
        contador_anexo += 1
        if linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".jpg"):
            #-------------------------------------------------------------------------------------------------------
            # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
            blob_data = linha_file_ref[1]
            #-----------------------------------------------------------------------------------
            # Obter a descrição da imagem via transform para econimizar consultas a API GEMINI
            # STATUS: desabilitado, pois a descrição gerada é pobre em detalhes
            #
            # descricao_imagem_exp = Canivete.extrair_texto_de_imagem(blob_data)
            # print(" \n Descrição da Imagem: \n " + descricao_imagem_exp + " \n ")
            #------------------------------------------------------------------------------------
            
            #-----------------------------------------------    
            # Decodificar o Base64
            #
            image_data = base64.b64decode(blob_data)
                
            if l_usa_Gemini:
                #----------------------------------------------------------------------------------------
                # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                image = Image.open(io.BytesIO(image_data))

                #----------------------------------------------------------------------------------------
                # Salva a imagem em um arquivo (ou exibe, se preferir)
                image.save("imagem_temporaria.jpg")  # Salva como PNG. Você pode ajustar o formato.
                # Ou, para exibir a imagem:
                # Usado apenas para teste do funcionamento da conversão do arquivo
                # image.show()
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                image_path  = "imagem_temporaria.jpg"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
            else:
                #-----------------------------------------------------------------------------------
                # Obter a descrição da imagem via biblioteca EasyOCR (sem uso de IA) para
                # economizar consultas à API Gemini, reservando-as para analisar o contexto geral
                #
                descricao_imagem_ocr = Canivete.extrair_texto_de_imagem_sem_ia_EasyOCR(image_data)
                print(" \n Descrição da Imagem: \n " + descricao_imagem_ocr + " \n ")
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: " + descricao_imagem_ocr
                
                if len(descricao_anexos) > 5000:
                    _instrucao = Persona.biblioteca_de_prompts(Persona.SINTETIZADOR_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica sem precisar ler desenas de páginas de error log."
                    question    = question + " Descrição do Anexo: \n " + str(contador_anexo) + " - descrição detalhada: "+ descricao_anexos
                    #arquivo_path  = "arquivo_temporario.pdf"
                    #descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                    
                    print(" \n Descrição Anexo - " + str(contador_anexo) +  " TAMANHO: " + str(len(descricao_anexos)) + " \n" + descricao_anexos)
                
        elif linha_file_ref[POS_ARQUIVO_TIPO].lower().endswith(".png"):
            # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
            #
            blob_data = linha_file_ref[1]
            
            #------------------------------------------------    
            # Decodificar o Base64
            image_data = base64.b64decode(blob_data)
                
            if l_usa_Gemini:
                #---------------------------------------------------------------------------------------------
                # Cria um objeto de imagem a partir dos dados binários extraídos na decodificação do Blob
                image = Image.open(io.BytesIO(image_data))
                #---------------------------------------------------------------------------------------------
                # Salva a imagem em um arquivo (ou exibe, se preferir)
                image.save("imagem_temporaria.png")  # Salva como PNG. Você pode ajustar o formato.
                # Ou, para exibir a imagem:
                # Usado apenas para testar a conversão do arquivo
                # image.show()
                #_instrucao  = "você é um assistente virtual especializado em descrever de forma detalhada prints de tela enviados em chamados de helpdesk para auxiliar um analista de tecnologia humano a compreender os anexos enviados pelos usuários de sistema nos chamados. Com sua descrição detalhada o analista de tecnologia humano deve ser capaz de compreender e tomar conhecimento de todos os detalhes presentes nos arquivos anexados aos chamados. Sendo assim, ao receber um anexo, analise o arquivo e forneça a descrição mais detalhada possível para que o analista de Tecnologia humano possa atender ao chamado dos usuários de sistema sem precisar fazer o download e acessar os arquivos anexos propriamente diretamente, bastante sua descrição dos mesmos."
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                image_path  = "imagem_temporaria.png"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini(image_path, "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
            else:
                #-----------------------------------------------------------------------------------
                # Obter a descrição da imagem via biblioteca EasyOCR (sem uso de IA) para
                # economizar consultas à API Gemini, reservando-as para analisar o contexto geral
                #
                descricao_imagem_ocr = Canivete.extrair_texto_de_imagem_sem_ia_EasyOCR(image_data)
                print(" \n Descrição da Imagem: \n " + descricao_imagem_ocr + " \n ")
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: " + descricao_imagem_ocr
                
                if len(descricao_anexos) > 5000:
                    _instrucao = Persona.biblioteca_de_prompts(Persona.SINTETIZADOR_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica sem precisar ler desenas de páginas de error log."
                    question    = question + " Descrição do Anexo: \n " + str(contador_anexo) + " - descrição detalhada: "+ descricao_anexos
                    #arquivo_path  = "arquivo_temporario.pdf"
                    #descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                    
                    print(" \n Descrição Anexo - " + str(contador_anexo) +  " TAMANHO: " + str(len(descricao_anexos)) + " \n" + descricao_anexos)
            
               
        elif linha_file_ref[0].lower().endswith(".pdf"):
            #------------------------------------------------------------------------------------------------------
            # Extrai o BLOB contendo a codificação da imagem em base64 (MELHORAR ISSO, pois pode ser .jpg ou .pdf)
            blob_data = linha_file_ref[POS_ARQUIVO_BLOB]
            
            #-------------------------------------------------------    
            # Decodifica o Base4
            pdf_data = base64.b64decode(blob_data)
            #-------------------------------------------------------    
            # Cria um "arquivo em memória" com os dados do PDF
            pdf_file = io.BytesIO(pdf_data)
                
            # Salva o arquivo PDF
            with open("arquivo_temporario.pdf", "wb") as f:
                f.write(pdf_file.getvalue())
                
            if l_usa_Gemini:
                #-------------------------------------------------------
                # Abrir o arquivo PDF com visualizador padrão
                # Usado apenas para testar a conversão do arquivo
                # os.startfile("arquivo_temporario.pdf") # para o Windows
                # Ou:
                # os.system("open arquivo.pdf") # Para macOS ou Linux
                    
                #-------------------------------------------------------
                # Ler informações do PDF (opicional)
                #
                pdf_reader = PdfReader(pdf_file)
                num_paginas = len(pdf_reader.pages)
                #print(f"Número de páginas: {num_paginas}")
                #-------------------------------------------------------
                # Obter informações do arquivo com Gemini
                #
                _instrucao = Persona.biblioteca_de_prompts(Persona.LEITOR_DE_ANEXOS_)
                question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica."
                arquivo_path  = "arquivo_temporario.pdf"
                descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                descricao_anexos += brain.analisar_com_gemini("", arquivo_path, question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                descricao_anexos = brain.limpa_texto(descricao_anexos)
            else:
                arquivo_path = "arquivo_temporario.pdf"
                descricao_anexos += Canivete.extrair_texto_de_pdf(arquivo_path)
                
                if len(descricao_anexos) > 5000:
                    _instrucao = Persona.biblioteca_de_prompts(Persona.SINTETIZADOR_)
                    question    = "por favor, analise o arquivo anexo e forneça uma descrição detalhada do mesmo de modo que um analista humano possa realizar sua análise técnica sem precisar ler desenas de páginas de error log."
                    question    = question + " Descrição do Anexo: \n " + str(contador_anexo) + " - descrição detalhada: "+ descricao_anexos
                    #arquivo_path  = "arquivo_temporario.pdf"
                    #descricao_anexos += "anexo " + str(contador_anexo) + " - descrição detalhada: "
                    descricao_anexos = brain.analisar_com_gemini("", "", question, _instrucao, 10, brain.GLOBAL_MODELO_MEDIO)
                    descricao_anexos = brain.limpa_texto(descricao_anexos)
                    
                    print(" \n Descrição Anexo - " + str(contador_anexo) +  " TAMANHO: " + str(len(descricao_anexos)) + " \n" + descricao_anexos)
        else:
            print("tipo de arquivo do anexo não previsto")
            pass
    print(" \n ANEXO - RESULTADO FINAL: \n " + descricao_anexos)
    return descricao_anexos
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# Função que conecta no banco do Sensr e retorna o resultado de uma query em uma tabela
# CHAMADOS NÃO CATEGORIZADOS
#
def listar_chamados_nao_categorizados(STATUS_, TICKET_START, TICKET_END, DEPTO_SELECIONADO):

    #---------------------
    # CONSTANTES
    #
    # TICKET
    ID_                     = 0
    ASSUNTO_                = 1
    DESC_                   = 2
    CIDADE_                 = 3
    UF_                     = 4
    PAIS_                   = 5
    TELEFONE_               = 6
    RAMAL_                  = 7
    MAIL_                   = 8
    CATEGORIA_              = 9
    SERVICO_                = 10
    TAREFA_                 = 11
    DEPARTAMENTO_           = 12
    EMPRESA_                = 13
    SLA_TAREFA_             = 14
    COMPLEXIDADE_TAREFA_    = 15
    DATA_TICKET_            = 16
    NOME_USUARIO_           = 17
    DEPTO_TECH_             = 18


    #---------------------
    # Variaveis
    # 
    dados_do_chamado    = ''
    lista_de_requisicoes = [] # {}
    contexto_dados      = ''
    
    #----------------------------------------------
    # Para testar IA GEMINI na análise MACRO
    # Criar cabeçalho do texto
    #
    contexto_dados  = "ID do Ticket;Data;Assunto;Descrição;Cidade;UF;País;Fone;Ramal;Email;Categoria Atual;Serviço Atual;Tarefa Atual;SLA Atual;Grau de Dificuldade;Departamento;Nome do Usuário;Empresa;Anexos"+" \n "
    
    # Query para buscar os Tickets Abertos no Sensr
    # CHAMADOS NÃO CATEGORIZADOS
    query_tickets = f'''
    SELECT
        tb_request.id_request AS ID,
        COALESCE(tb_request.subject, '') AS ASSUNTO,
        COALESCE(tb_request.description, '') AS DESC,
        COALESCE(tb_city.name, '') AS CIDADE,
        COALESCE(tb_state.name, '') AS UF,
        COALESCE(tb_country.name, '') AS PAIS,
        COALESCE(tb_person.phone, '') AS TELEFONE,
        COALESCE(tb_person.ramal, '') AS RAMAL_USER,
        COALESCE(tb_person.email, '') AS MAIL,
        COALESCE(tb_category.name, '') AS CATEGORIA,
        COALESCE(tb_catalog_service.name, '') AS SERVICO,
        COALESCE(tb_catalog_task.name, '') AS TAREFA,
        COALESCE(tb_department.name, '') AS DEPARTAMENTO,
        COALESCE(EMPRESA.name, '') AS EMPRESA_USER,
        COALESCE(tb_catalog_task.time_sla, 0) AS SLA_TAREFA,
        COALESCE(tb_catalog_task.complexity, '') AS COMPLEXIDADE_TAREFA,
        tb_request.dt_cad AS DATA_INPUT,
        tb_person.name as NOME,
        DEPTO_TECH.name
    FROM tb_request
    LEFT JOIN tb_tickets ON tb_tickets.fk_id_request = tb_request.id_request
    LEFT JOIN tb_user ON tb_user.id_user = tb_request.user_cad::integer
    LEFT JOIN tb_person ON tb_person.id_person = tb_user.fk_id_person
    LEFT JOIN tb_city ON tb_city.id_city = tb_user.id_city
    LEFT JOIN tb_state ON tb_state.id_state = tb_user.id_state
    LEFT JOIN tb_country ON tb_country.id_country = tb_user.id_country
    LEFT JOIN tb_category ON tb_category.id_category = tb_request.fk_id_category
    LEFT JOIN tb_catalog_service ON tb_catalog_service.id_catalog_service = tb_request.fk_id_catalog_service
    LEFT JOIN tb_catalog_task ON tb_catalog_task.id_catalog_task = tb_request.fk_id_catalog_task
    LEFT JOIN tb_department ON tb_department.id_department = tb_user.fk_id_department
    LEFT JOIN tb_company ON tb_company.id_company = tb_request.fk_id_company
    LEFT JOIN tb_person AS EMPRESA ON EMPRESA.id_person = tb_company.fk_id_person
    LEFT JOIN tb_department AS DEPTO_TECH ON DEPTO_TECH.id_department = tb_request.fk_id_department
    WHERE
        tb_request.status = '{str(STATUS_)}'
        AND tb_request.id_request >= '{str(TICKET_START)}'
        AND tb_request.id_request <= '{str(TICKET_END)}'
        AND tb_request.fk_id_department = '{str(DEPTO_SELECIONADO)}'
    ORDER BY tb_request.id_request
    '''
    #res = consulta_sensr(False,"select email_user,sla_task,id_user_name,company_name,category_name,catalog_service_name,catalog_task_name,department_name,group_tech_name,user_cad_name,sla,notes,dt_up,dt_cad,status,description,subject,id_tickets from tb_tickets where status = 'Open' Order By id_tickets ")
    res = consulta_sensr(False, query_tickets)
    #print("CONSULTA TICKETS ABERTOS:")
    # Varre o resultado da query, ticket por ticket
    for linha in res:
        
        
        
        # Obtem os dados do chamado para análise
        dados_do_chamado = 'Dados do Chamado: '
        dados_do_chamado +=  "\n" + " ID da Requisição: " + str(linha[ID_])
        dados_do_chamado +=  "\n" + " Data do Ticket: " + str(linha[DATA_TICKET_])
        dados_do_chamado +=  "\n" + " Assunto da Requisição: " + linha[ASSUNTO_]
        dados_do_chamado +=  "\n" + " Descrição da Requisição: " + linha[DESC_]
        dados_do_chamado +=  "\n" + " Cidade do Usuário: " + linha[CIDADE_]
        dados_do_chamado +=  "\n" + " UF do Usuário: " + linha[UF_]
        dados_do_chamado +=  "\n" + " País do Usuário: " + linha[PAIS_]
        dados_do_chamado +=  "\n" + " Telefone do Usuário: " + linha[TELEFONE_]
        dados_do_chamado +=  "\n" + " Ramal do Usuário: " + linha[RAMAL_]
        dados_do_chamado +=  "\n" + " Email do Usuário: " + linha[MAIL_]
        dados_do_chamado +=  "\n" + " Categoria da Requisição: " + linha[CATEGORIA_]
        dados_do_chamado +=  "\n" + " Serviço da Requisição: " + linha[SERVICO_]
        dados_do_chamado +=  "\n" + " Tarefa da Requisição: " + linha[TAREFA_]
        dados_do_chamado +=  "\n" + " SLA da Tarefa: " + str(linha[SLA_TAREFA_])
        dados_do_chamado +=  "\n" + " Complexidade da Tarefa: " + linha[COMPLEXIDADE_TAREFA_]
        dados_do_chamado +=  "\n" + " Departamento do Usuário: " + linha[DEPARTAMENTO_]
        dados_do_chamado +=  "\n" + " Empresa do Usuário: " + linha[EMPRESA_]
        dados_do_chamado +=  "\n" + " Nome do Usuário: " + linha[NOME_USUARIO_]
        
        print(" \n Dados do Ticket: \n " + dados_do_chamado)
        
        info_truncada = ''
        
        id_ticket       = str(linha[ID_])
        data_ticket     = str(linha[DATA_TICKET_])
        
        if len(linha[ASSUNTO_]) > 100:
            info_truncada = linha[ASSUNTO_][:100] + "..."
        else:
            info_truncada = linha[ASSUNTO_]
        assunto_ticket  = info_truncada
        assunto_ticket  = Canivete.limpa_texto(assunto_ticket, ';', '')
        assunto_ticket  = Canivete.limpa_texto(assunto_ticket, '</p>', ' ')
        assunto_ticket  = Canivete.limpa_texto(assunto_ticket, '<p>', ' ')
        assunto_ticket  = Canivete.limpa_texto(assunto_ticket, '<br>', ' ')
        assunto_ticket  = Canivete.limpa_texto(assunto_ticket, '\\n', '. ')
        assunto_ticket  = Canivete.limpa_texto(assunto_ticket, '\r\n', '. ')
        
        
        info_truncada = ''
        if len(linha[DESC_]) > 300:
            info_truncada = linha[DESC_][:300] + "..."
        else:
            info_truncada = linha[DESC_]
        desc_ticket     = info_truncada
        desc_ticket  = Canivete.limpa_texto(desc_ticket, ';', '')
        desc_ticket  = Canivete.limpa_texto(desc_ticket, '</p>', ' ')
        desc_ticket  = Canivete.limpa_texto(desc_ticket, '<p>', ' ')
        desc_ticket  = Canivete.limpa_texto(desc_ticket, '<br>', ' ')
        desc_ticket  = Canivete.limpa_texto(desc_ticket, '\\n', '. ')
        desc_ticket  = Canivete.limpa_texto(desc_ticket, '\r\n', '. ')
        
        cidade_ticket   = linha[CIDADE_]
        uf_ticket       = linha[UF_]
        pais_ticket     = linha[PAIS_]
        fone_ticket     = linha[TELEFONE_]
        ramal_ticket    = linha[RAMAL_]
        mail_ticket     = linha[MAIL_]
        cat_ticket      = linha[CATEGORIA_]
        ser_ticket      = linha[SERVICO_]
        tar_ticket      = linha[TAREFA_]
        sla_ticket      = str(linha[SLA_TAREFA_])
        complex_ticket  = linha[COMPLEXIDADE_TAREFA_]
        dept_ticket     = linha[DEPARTAMENTO_]
        emp_ticket      = linha[EMPRESA_]
        nome_user       = linha[NOME_USUARIO_]
        depart_tech     = linha[DEPTO_TECH_]
        
        
        anexos_ticket   = busca_descricao_anexos_tickets(id_ticket)
        
        #-------------------------------------------------------------------------------
        # Para textar analise MACRO VIA IA GEMINI
        #
        contexto_dados += id_ticket + ";" + data_ticket + ";" + assunto_ticket + ";" + desc_ticket + ";" + cidade_ticket + ";" + uf_ticket + ";" + pais_ticket + ";" + fone_ticket + ";" + ramal_ticket + ";" + mail_ticket + ";" + cat_ticket + ";" + ser_ticket + ";" + tar_ticket + ";" + sla_ticket + ";" + complex_ticket + ";" + dept_ticket + ";" + emp_ticket + ";" + anexos_ticket + "\n"
        
        registro= {
            "ID do Ticket": id_ticket,
            "Data": data_ticket,
            "Assunto": assunto_ticket,
            "Descrição": desc_ticket,
            "Cidade": cidade_ticket,
            "UF": uf_ticket,
            "País": pais_ticket,
            "Fone": fone_ticket,
            "Ramal": ramal_ticket,
            "Email": mail_ticket,
            "Categoria Atual": cat_ticket,
            "Serviço Atual": ser_ticket,
            "Tarefa Atual": tar_ticket,
            "SLA Atual": sla_ticket,
            "Grau de Dificuldade": complex_ticket,
            "Departamento do Usuário": dept_ticket,
            "Departamento Técnico": depart_tech,
            "Empresa": emp_ticket,
            "Nome do Usuário": nome_user,
            "Anexos": anexos_ticket,
        }
        lista_de_requisicoes.append(registro)
        # tabela_categorizacao[linha] = lista_req
        
        print(" \n FIM PARCIAL \n ")
    arq_csv     = 'lista_de_tickets_nao_categorizados.csv'
    campos_csv  = ["ID do Ticket", "Data", "Assunto", "Descrição", 
                   "Cidade", "UF", "País", "Fone", "Ramal", "Email", 
                   "Categoria Atual", "Serviço Atual", "Tarefa Atual", 
                   "SLA Atual", "Grau de Dificuldade", "Departamento do Usuário", "Departamento Técnico", 
                   "Empresa", "Nome do Usuário", "Anexos"]
    Canivete.converter_para_csv_v2(lista_de_requisicoes, arq_csv,campos_csv )
    
    _instrucao_ia        = Persona.biblioteca_de_prompts(Persona.ANALISTA_GENERALISTA_2_)
    _contexto_completo   = f"""
                        Peço que você analise a lista de tickets não categorizados do departamento de TI (em formato CSV) que 
                        envio abaixo, e me retorne um relatório sobre cada ticket, ordenando a resposta conforme a 
                        prioridade que achar melhor para cada caso.
                        Por favor, responda formatando o texto com MarkDown (com quebras de linhas, marcas de título e subtítulo, palavras destacas, etc).
                        Analise com calma e leve o tempo que precisar para responder.
                        """
    _contexto_completo   += contexto_dados
    resposta_ia          = brain.analisar_com_gemini('','',_contexto_completo,_instrucao_ia,10,brain.GLOBAL_MODELO_PESADO)
    # resposta_ia          = brain.limpa_texto(resposta_ia)
    print(" \n RESPOSTA DA IA \n" + resposta_ia)
    
    # Salvar como arquivo de texto
    with open("arquivo_texto.txt", "w") as arquivo:
        arquivo.write(resposta_ia)
    
    print(" \n FIM \n ")
    
    matrix_retorno = [resposta_ia, pd.DataFrame(lista_de_requisicoes)]
    return matrix_retorno
#
# FIM
#---------------------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------------------
# START
# Outros testes iniciais
#---------------------------------------------------------------------------------------------------------------

# Open
# Resolved
# In Progress

testar = False

if testar:
    
    resposta_da_ia = analise_profunda_tickets_categorizados('Open', 'R6097', 'R6097')
    print("\n RESPOSTA - TICKET EM ANDAMENTO \n  " + resposta_da_ia)
    
    resposta_da_ia = analise_profunda_ticket_nao_categorizados('Open', '5649', '5649')
    print(" \n sem markdownify \n " + resposta_da_ia)
    resposta_da_ia = markdownify.markdownify(resposta_da_ia)
    print(" \n com markdownify \n " + resposta_da_ia)
    print(analise_profunda_ticket_nao_categorizados('Open', '5649', '5649'))
    
    listar_chamados_nao_categorizados('Open', '0000', '9999')
    
    consulta_chamados_nao_categorizados('Open', '5680', '5680')
    consulta_chamados_abertos('In Progress', '5394', '5394')

    print("fim")

