import parametros_globais as OneRing

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
# from dotenv import load_dotenv

# load_dotenv(dotenv_path='ambiente.env')



ambiente_local = OneRing.TESTE_LOCAL_ # False
if ambiente_local:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='ambiente.env')
    EMAIL_REMETENTE_GMAIL = os.getenv('EMAIL_REMETENTE') # Seu email Gmail (remetente)
    SENHA_REMETENTE_GMAIL = os.getenv('SENHA_EMAIL_REMETENTE') # Senha do seu email Gmail ou App Password
else:
    import streamlit as st
    EMAIL_REMETENTE_GMAIL = st.secrets["EMAIL_REMETENTE"] # Seu email Gmail (remetente)
    SENHA_REMETENTE_GMAIL = st.secrets["SENHA_EMAIL_REMETENTE"] # Senha do seu email Gmail ou App Password
    
    

#---------------------------------------------------------------------------------------------------------------
# Função para envio de email usando Gmail SMTP (sem OAuth - APENAS PARA TESTES!)
#
def enviar_email_gmail_smtp(destinatario, assunto, corpo, arquivos_anexos=None):
    """Envia um email usando o Gmail SMTP (sem OAuth - INSEGURO! APENAS PARA TESTES)."""

    if not EMAIL_REMETENTE_GMAIL or not SENHA_REMETENTE_GMAIL:
        print('Erro: Email remetente Gmail e/ou senha não configurados nas variáveis de ambiente.')
        return False

    mensagem = MIMEMultipart()
    mensagem['From'] = EMAIL_REMETENTE_GMAIL
    mensagem['To'] = destinatario
    mensagem['Subject'] = assunto
    mensagem.attach(MIMEText(corpo, 'html'))

    if arquivos_anexos:
        for arquivo in arquivos_anexos:
            parte = MIMEBase('application', 'octet-stream')
            parte.set_payload(open(arquivo, 'rb').read())
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(arquivo)}')
            mensagem.attach(parte)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as servidor_smtp: # porta padrão 587 # Conexão com servidor Gmail SMTP
            servidor_smtp.starttls() # Inicia a encriptação TLS
            servidor_smtp.login(EMAIL_REMETENTE_GMAIL, SENHA_REMETENTE_GMAIL) # Login com email e senha
            texto = mensagem.as_string()
            servidor_smtp.sendmail(EMAIL_REMETENTE_GMAIL, destinatario, texto) # Envia o email
        return True
    except Exception as e:
        print(f'Erro ao enviar email via Gmail SMTP: {e}')
        return False
# 
# FIM
#---------------------------------------------------------------------------------------------------------------

teste = False
if teste:
    arquivos = ['arquivo_temporario.pdf']
    destino     = 'eder.silva@luft.com.br'
    assunto     = 'Categorização de Chamados'
    corpo       = 'Relatório de Categorização de Chamados'
    
    enviar_email_gmail_smtp(destino, assunto, corpo, arquivos)
    print(" \n ")