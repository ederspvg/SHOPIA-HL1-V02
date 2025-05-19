import parametros_globais as OneRing

import os
from serpapi import GoogleSearch
# from dotenv import load_dotenv
# load_dotenv(dotenv_path='ambiente.env')

ambiente_local = OneRing.TESTE_LOCAL_ # False
if ambiente_local:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='ambiente.env')
    chave_serpapi = os.getenv('SERP_API_KEY')
else:
    import streamlit as st
    chave_serpapi = st.secrets["SERP_API_KEY"]

#---------------------------------------------------------------------------------------------------------------
# Função que busca na internet e retorna o resultado da busca
#
def pesquisar_na_internet(pesquisa_):
    """
    Realiza uma busca na internet usando a API do SerpAPI e retorna o resultado em formato de texto.

    Args:
        pesquisa_ (str): A string de pesquisa.

    Returns:
        str: O resultado da busca em formato de texto, ou None em caso de erro.
    """
    try:
        params = {
            "q": pesquisa_,
            "api_key": chave_serpapi # "e0bd547936186b770c20324f4df7f54783411b35a88528c39fb9c4fa3202d12e" #  Substitua pela sua chave de API
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        # Extrai os resultados da pesquisa e formata em texto
        text_results = ""
        for result in results.get("organic_results", []):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")

            text_results += f"Título: {title}\n"
            text_results += f"Resumo: {snippet}\n"
            text_results += f"Link: {link}\n\n"

        return text_results

    except Exception as e:
        print(f"Erro na pesquisa: {e}")
        return None
#
# Fim
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# Start
#
if False:
    # Exemplo de uso
    pesquisa_ = input("O que deseja pesquisar?")
    resultado_busca = pesquisar_na_internet(pesquisa_)

    if resultado_busca:
        print(resultado_busca)
#
# Fim
#---------------------------------------------------------------------------------------------------------------