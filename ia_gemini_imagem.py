
import os
from dotenv import load_dotenv
from datetime import date
from pathlib import Path
import base64
import PIL.Image # pip install Pillow
import time
from google import genai
from google.genai import types

load_dotenv(dotenv_path='ambiente.env')
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
#---------------------------------------------------------------------------------------------------------------
# Função de IA do Gemini para gerar imagens
#
def gerar_imagem(prompt_):
    """
    Gera uma imagem a partir de um texto usando a API do Gemini.

    Args:
        prompt (str): O texto descritivo da imagem a ser gerada.

    Returns:
        bytes: Os dados da imagem em formato bytes, ou None em caso de erro.
    """
    
    resposta = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt_,
            config=types.GenerateImagesConfig(
                negative_prompt='people',
                aspect_ratio='9:16',
                safety_filter_level='BLOCK_ONLY_HIGH',
                number_of_images=1,
                include_rai_reason=True,
                output_mime_type='image/jpeg'
            )
        )
    resposta.generated_images[0].image.show()
        

#
# FIM
#---------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------
# START
# 

teste = False #True

if teste:
    # Exemplo de uso
    prompt_img = "Um gato siamês deitado em um sofá vermelho, com óculos de sol e um chapéu de palha."
    gerar_imagem(prompt_img)