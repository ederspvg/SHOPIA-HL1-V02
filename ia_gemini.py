import parametros_globais as OneRing

import os
import time
from dotenv import load_dotenv
import streamlit as st
from datetime import date
from pathlib import Path
import google.generativeai as genai
from google.api_core.exceptions import InternalServerError
import base64
import PIL.Image # pip install Pillow
import time

import google_search as buscador
import prompts_ia as Persona

ambiente_local = OneRing.TESTE_LOCAL_ # False
if ambiente_local:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='ambiente.env')
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
else:
    import streamlit as st
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])






#---------------------------------------------------------------------------------------------------------------
# Variáveis de escopo global
#
GLOBAL_MODELO_LEVE      = 'gemini-1.5-flash'
GLOBAL_MODELO_MEDIO     = 'gemini-2.0-flash-exp'
GLOBAL_MODELO_PESADO    = 'gemini-2.0-flash-thinking-exp'
GLOBAL_MODELO_EXP       = 'gemini-2.0-flash-thinking-exp-01-21'
GLOBAL_DORMENCIA        = 30


# Função que gera prompt (para não precisar colar um texto muito grande)
#
def gerar_prompt(): 
    return f""" 
            Você é um consultor especialista em tecnologia da informação que trabalha na Luft; um grupo logístico que presta serviços de transporte e armazenagem de mercadorias de diversos setores. Neste caso, os usuários de computador do grupo Luft irão apresentar as mais diversas dúvidas de Tecnologia da Informação (às vezes apresentando prints de tela).
            Com base em seus conhecimentos gerais nos mais diversos softwares e sistemas (como o ERP Protheus, ESL, Silt, Pacoe Office, Windows, e-mail do Gmail, Infraestrutura, etc) responda as dúvidas dos usuários como se estivesse explicando algo para uma pessoa completamente leiga em tecnologia da informação.
            Lembre-se de explicar para o usuário se a mensagem na tela trata-se de um erro ou de um alerta (erros de sistema e alertas possuem simbolos diferentes para ajudar a diferenciar cada caso). Quando se trata de um erro, o caminho a seguir é abrir um chamado com a equipe de suporte. Quando o ícone da mensagem apresentada na tela é de um alerta, é provável que a situação pode ser resolvida pelo próprio usuário após analisar o processo que está realizando.
            Para dúvidas sobre o Protheus, consulte também a documentação do fabricante antes de responder ao usuário: https://tdn.totvs.com/display/public/PROT/Protheus++12
            Além disso, para registrar essa consulta do usuário em um FAQ (uma Base de conhecimento de Perguntas Mais Frequêntes), faça um relatório com as principais informações sobre a dúvida como por exemplo: 
            um título que resuma a natureza da dúvida de forma clara, nome do sistema ou programa, nome da rotina executada no sistema ou programa (por exemplo: no Protheus pode ser o nome da rotina, no Office pode ser o nome do programa do pacote Office), nome do usuário de acesso ao sistema (se houver), data, hora, processo executado pelo usuário, mensagem de erro, explicação resumidada do erro, passos a seguir para solucionar o problema (exemplo: contatar a equipe de suporte da Luft, reiniciar a máquina, preencher a informação solicitada pelo sistema ou programa, etc). 
            Por fim, escreva para o usuário um texto endereçado para o time de suporte de tecnologia da informação do grupo Luft, caso o usuário precise abrir chamado, de modo que ele não precise escrever o texto do chamado. 
            O texto para a equipe de chamado deve fornecer o máximo de informações possíveis de acordo com o que é fornecido pelo print do usuário e pelo texto de dúvida que este te enviou. 
            Resposta para o usuário: deve ser simples e clara para um leigo de tecnologia compreender o necessário, indicando os passos a seguir. 
            Relatório para FAQ contendo: 
            - Título da dúvida; 
            - Dados (nome do sistema ou programa, login se houver, rotina usada no sistema ou programa, data, e qualquer outra informação que se possa deduzir com base no print ou prompt do usuário); 
            - Solução: indica a solução para o usuário. 
            Mas, caso não haja uma solução e seja necessário acionar a equipe de Tecnologia da Informação da Luft, crie o texto abaixo: 
            Oriente o usuário a abrir um chamado usando os dados abaixo: 
            - Título do chamado; 
            - Descrição do chamado com o máximo de informação. 
            """
#---------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------
# Função que remove símbolos do texto. No momento, apenas '*' e '#'
#
def limpa_texto(_texto):
    sujeira = True
    contador = 0
    while sujeira:
        if '*' in _texto:
            _texto = _texto.replace('*', '')
        elif '#' in _texto:
            _texto = _texto.replace('#', '')
        else:
            sujeira = False
            contador += 1
    return _texto


#---------------------------------------------------------------------------------------------------------------
# Função de Chat do GEMINI AI
#
# def analisar_imagem_com_gemini(_image_path, _pdf_path, _contexto, _instrucao, _tentativas_restantes):
def analisar_com_gemini(_image_path, _pdf_path, _contexto, _instrucao, _tentativas_restantes, _modelo_de_pensamento):
    
    time.sleep(GLOBAL_DORMENCIA)
    
    _prompt = _instrucao + ' sendo assim, responda: ' + _contexto # gerar_prompt()
    #CONTROLES INTERNOS - APENAS PARA APRENDIZADO E UTILIDADES GERAIS
    #
    logic_lista_modelos         = True
    logic_lista_config_modelos  = False
    logic_usa_Chat              = True
    
    # Checa se é para listar os modelos
    #
    if logic_lista_modelos:
        # listar modelos
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
        #
    #
        
    # Modelo de IA: serve para imagem e texto
    #
    # MODELO ESTÁVEL: 'gemini-1.5-flash'
    # MODELO EXPERIMENTAL: 'gemini-2.0-flash-exp'
    if _modelo_de_pensamento != '':
        modelo_escolhido = _modelo_de_pensamento
    else:
        modelo_escolhido = GLOBAL_MODELO_LEVE
    
    #model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=_instrucao) # o gemini-1.5-pro é gratuito, mas tem um limite de uso diario. O flash não possui o limite diario: https://developers.googleblog.com/pt-br/gemini-15-pro-and-15-flash-now-available/
    #model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=_instrucao)
    # modelo_escolhido = 'gemini-2.0-flash-exp'
    # modelo_escolhido = 'gemini-1.5-flash'
    # modelo_escolhido = 'gemini-2.0-flash-thinking-exp-01-21'
    # modelo_escolhido = 'gemini-2.0-flash-thinking-exp'
    # modelo_escolhido = 'gemini-2.0-pro-exp-02-05'
    # modelo_escolhido = 'gemini-2.0-flash-001'
    
    model = genai.GenerativeModel(modelo_escolhido, system_instruction=_instrucao)
    
    #
    
    # Mostra as configurações do modelo
    #
    if logic_lista_config_modelos:
        print(f"CONFIG - candidate_count: {model._generation_config.candidate_count}")
        print(f"CONFIG - temperature: {model._generation_config.temperature}")
        print(f"CONFIG - max_output_tokens: {model._generation_config.max_output_tokens}")
        print(f"CONFIG - stop_sequences: {model._generation_config.stop_sequences}")
    
    # Inicia modelo de Chat
    #
    chat = model.start_chat(
        history=[
            {"role": "user", "parts": "Olá!"},
            #{"role": "model", "parts": "Haja como um consultor especializado em Tecnologia da Informação, esclarecendo dúvidas sobre os mais diversos sistemas e softwares de computador."},
            {"role": "model", "parts": _prompt},
        ]
    )
    #
    
    # Carregar a imagem
    #
    if _image_path == '':
        print("Não há imagem")
        img = 'Não tenho uma imagem da espécie para mostrar'
    else:
        print("Há imagem")
        img = PIL.Image.open(_image_path)
        
    # Carregar o pdf
    #
    if _pdf_path == '':
        print("Não há pdf")
        arquivo_pdf = 'Não tenho arquivo pdf para mostrar'
    else:
        print("Há pdf")
        arquivo_pdf = genai.upload_file(_pdf_path, display_name="")
    
    # Converte a Imagem em um texto que a IA consegue interpretar
    #
    # response = model.generate_content(img)
    
    for tentativa in range(_tentativas_restantes):
         try:
             # Gera conteúdo com a imagem e contexto
             #
             if logic_usa_Chat:
                #resposta = chat.send_message([_contexto, img, arquivo_pdf],
                resposta = chat.send_message([_prompt, img, arquivo_pdf],
                                                generation_config=genai.types.GenerationConfig(temperature=1)
                                                )
                resposta.resolve()
             else:
                #resposta = model.generate_content([_contexto, img, arquivo_pdf],
                resposta = model.generate_content([_prompt, img, arquivo_pdf],
                                                    generation_config=genai.types.GenerationConfig(temperature=1))
                resposta.resolve()
             #
             #global_ultima_especie_consultada = resposta.text
             return resposta.text
             #
         except InternalServerError as e:
            if tentativa < _tentativas_restantes - 1:
                print(f"Erro interno no servidor Gemini. Tentando novamente ({_tentativas_restantes - tentativa - 1} tentativas restantes).")
                time.sleep(2)  # Ajuste o tempo de espera entre tentativas
            else:
                print("Todas as tentativas falharam. Erro:", e)
                return None  # Retorna None em caso de falha após todas as tentativas

    #Código nunca deve chegar aqui, a menos que tentativas_restantes seja 0
    return None
#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------
# TESTE
#
teste = False #True # False

if teste:
    conversa = True

    interacao_usuario   = input("\n Informe o que você quer?   \n")
    imagem_             = input("\n Informe o caminho da imagem:   \n")
    #instrucao_IA        = 'Você é um consultor especialista em tecnologia da informação que trabalha na Luft; um grupo logístico que presta serviços de transporte e armazenagem de mercadorias de diversos setores. Neste caso, os usuários de computador do grupo Luft irão apresentar as mais diversas dúvidas de Tecnologia da Informação (às vezes apresentando prints de tela). Com base em seus conhecimentos gerais nos mais diversos softwares e sistemas (como o ERP Protheus, ESL, Silt, Pacoe Office, Windows, e-mail do Gmail, Infraestrutura, etc) responda as dúvidas dos usuários como se estivesse explicando algo para uma pessoa completamente leiga em tecnologia da informação. Além disso, para registrar essa consulta do usuário em um FAQ (uma Base de conhecimento de Perguntas Mais Frequêntes), faça um relatório com as principais informações sobre a dúvida como por exemplo: um título que resuma a natureza da dúvida de forma clara, nome do sistema ou programa, nome da rotina executada no sistema ou programa (por exemplo: no Protheus pode ser o nome da rotina, no Office pode ser o nome do programa do pacote Office), nome do usuário de acesso ao sistema (se houver), data, hora, processo executado pelo usuário, mensagem de erro, explicação resumidada do erro, passos a seguir para solucionar o problema (exemplo: contatar a equipe de suporte da Luft, reiniciar a máquina, preencher a informação solicitada pelo sistema ou programa, etc). Por fim, escreva para o usuário um texto endereçado para o time de suporte de tecnologia da informação do grupo Luft, caso o usuário precise abrir chamado, de modo que ele não precise escrever o texto do chamado. O texto para a equipe de chamado deve fornecer o máximo de informações possíveis de acordo com o que é fornecedio pelo print do usuário e pelo texto de dúvida que este te enviou.'
    instrucao_IA        = Persona.biblioteca_de_prompts(Persona.BIBLIOTECARIO_)
    arquivo_pdf         = input("\n Informe o caminho do PDF:   \n")  #'' #'MANUAL CADASTRO DE PRODUTOS.pdf'
    resposta_ChatBox    = analisar_com_gemini(imagem_, arquivo_pdf, interacao_usuario, instrucao_IA, 10)
    resposta_ChatBox    = limpa_texto(resposta_ChatBox)
    time.sleep(3)
    print(f"Resposta do ChatBox - como pesquisar na internet sobre o contexto apresentado: \n {resposta_ChatBox}")
    
    retorno_busca       = buscador.pesquisar_na_internet(resposta_ChatBox)
    arquivo_pdf         = resposta_ChatBox
    #instrucao_IA        = Persona.biblioteca_de_prompts(Persona.ANALISTA_COMPLETO_)
    instrucao_IA        = Persona.biblioteca_de_prompts(Persona.ANALISTA_COMPLETO_2_)
    novo_contexto       = interacao_usuario + " Resultado da Busca na Internet: \n " + retorno_busca
    resposta_ChatBox    = analisar_com_gemini(imagem_, arquivo_pdf, interacao_usuario, instrucao_IA, 10)
    resposta_ChatBox    = limpa_texto(resposta_ChatBox)
    
    print(f"Resposta do ChatBox - Analista Completo: \n {resposta_ChatBox}")
    
    print("\n")

    while conversa:
        interacao_usuario   = input("\n Informe o que você quer?   \n")
        imagem_             = input("\n Informe o caminho da imagem:   \n")
        #instrucao_IA        = 'Você é um consultor especialista em tecnologia da informação que trabalha na Luft; um grupo logístico que presta serviços de transporte e armazenagem de mercadorias de diversos setores. Neste caso, os usuários de computador do grupo Luft irão apresentar as mais diversas dúvidas de Tecnologia da Informação (às vezes apresentando prints de tela). Com base em seus conhecimentos gerais nos mais diversos softwares e sistemas (como o ERP Protheus, ESL, Silt, Pacoe Office, Windows, e-mail do Gmail, Infraestrutura, etc) responda as dúvidas dos usuários como se estivesse explicando algo para uma pessoa completamente leiga em tecnologia da informação. Além disso, para registrar essa consulta do usuário em um FAQ (uma Base de conhecimento de Perguntas Mais Frequêntes), faça um relatório com as principais informações sobre a dúvida como por exemplo: um título que resuma a natureza da dúvida de forma clara, nome do sistema ou programa, nome da rotina executada no sistema ou programa (por exemplo: no Protheus pode ser o nome da rotina, no Office pode ser o nome do programa do pacote Office), nome do usuário de acesso ao sistema (se houver), data, hora, processo executado pelo usuário, mensagem de erro, explicação resumidada do erro, passos a seguir para solucionar o problema (exemplo: contatar a equipe de suporte da Luft, reiniciar a máquina, preencher a informação solicitada pelo sistema ou programa, etc). Por fim, escreva para o usuário um texto endereçado para o time de suporte de tecnologia da informação do grupo Luft, caso o usuário precise abrir chamado, de modo que ele não precise escrever o texto do chamado. O texto para a equipe de chamado deve fornecer o máximo de informações possíveis de acordo com o que é fornecedio pelo print do usuário e pelo texto de dúvida que este te enviou.'
        #arquivo_pdf         = ''
        arquivo_pdf         = input("\n Informe o caminho do PDF: ")
        resposta_ChatBox    = analisar_com_gemini(imagem_, arquivo_pdf, interacao_usuario, instrucao_IA, 10)
        resposta_ChatBox    = limpa_texto(resposta_ChatBox)
        time.sleep(3)
        print(f"Resposta do ChatBox: {resposta_ChatBox}")
        print("\n")
#---------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------