import streamlit as st
from ia_gemini import analisar_imagem_com_gemini, limpa_texto, gerar_prompt
from PIL import Image

#---------------------------------------------------
# PARA Ativiar a aplicação em StreamLit:
# streamlit run app.py
#---------------------------------------------------

st.title("Consultor de TI")
st.write("Faça suas perguntas sobre tecnologia da informação.")

# Instrução
_instrucao = gerar_prompt()

# Campo de entrada para a pergunta
question = st.text_input("Digite sua pergunta:")

# Campo de upload para a imagem
uploaded_file = st.file_uploader("Envie um print (opcional):", type=["png", "jpg", "jpeg"])

# Botão para enviar a pergunta
if st.button("Enviar"):
    if question:
        # Salvar a imagem enviada, se houver
        image_path = ""
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            image_path = "uploaded_image.png"
            image.save(image_path)
        
        # Chamar a função de análise da imagem com a pergunta
        resposta = analisar_imagem_com_gemini(image_path, "", question, _instrucao, 3)
        resposta = limpa_texto(resposta)
        
        # Exibir a resposta
        st.write("Resposta:", resposta)
        
        # Exibir a imagem enviada, se houver
        if uploaded_file is not None:
            st.image(image, caption="Print enviado", use_column_width=True)
    else:
        st.write("Por favor, digite uma pergunta.")
