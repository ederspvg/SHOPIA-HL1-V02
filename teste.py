import parametros_globais as OneRing
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from PIL import Image
from typing import List
import shutil

# Configuração da API Gemini
load_dotenv(dotenv_path='ambiente.env')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Configurações do ChromaDB (mantidas fora da classe, como globais)
PERSIST_DIRECTORY = OneRing.PASTA_BANCO # "chroma_db_v13"
PERSIST_COLECAO_NOME = OneRing.NOME_COLECAO # "biblioteca_v13"
PERSIST_PASTA_BIBLIOTECA = OneRing.PASTA_BIBLIOTECA # "biblioteca_geral"

# Classe de Embedding compatível com ChromaDB
class EmbeddingFunction:
    def __init__(self):
        self.model = SentenceTransformer('all-mpnet-base-v2')
    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.model.encode(input).tolist()

class SistemaRAG:
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Classe do Sistema RAG para gerenciamento de coleções e consultas
    #
    def __init__(self, colecao_nome=PERSIST_COLECAO_NOME, diretorio_persistencia=PERSIST_DIRECTORY):
        """Inicializa o Sistema RAG, conectando ao ChromaDB e configurando embedding."""
        print(f" [i] Inicializando SistemaRAG para coleção: '{colecao_nome}' em '{diretorio_persistencia}'")
        self.colecao_nome = colecao_nome
        self.diretorio_persistencia = diretorio_persistencia
        self.client = chromadb.PersistentClient(path=self.diretorio_persistencia)
        self.colecao = None # Inicializa colecao como None, será conectado/criado nos métodos
        self.embedding_fn = EmbeddingFunction()  # Instância única
        print(f" [i] SistemaRAG inicializado.")
        
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função MOVER ARQUIVO
    #
    def _mover_arquivo(self, caminho_arquivo: str, pasta_documentos: str):
        """Move o arquivo processado para a pasta 'lidos'."""
        pasta_lidos = os.path.join(pasta_documentos, "lidos")
        os.makedirs(pasta_lidos, exist_ok=True)
        nome_arquivo = os.path.basename(caminho_arquivo)
        destino = os.path.join(pasta_lidos, nome_arquivo)
        try:
            shutil.move(caminho_arquivo, destino)
            print(f"   [+] Arquivo '{nome_arquivo}' movido para '{pasta_lidos}'.")
        except Exception as e:
            print(f"   [-] Erro ao mover '{nome_arquivo}': {str(e)}")
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função LER ARQUIVO
    #
    def _ler_arquivo(self, caminho: str) -> List[str]:
        """Método interno para ler arquivos, direcionando para a função correta."""
        if caminho.endswith(".pdf"):
            return self._ler_pdf(caminho)
        elif caminho.endswith(".txt"):
            return self._ler_txt(caminho)
        elif caminho.endswith(".docx"):
            return self._ler_docx(caminho)
        raise ValueError("Formato não suportado")
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função LER PDF
    #
    def _ler_pdf(self, caminho: str) -> List[str]:
        """Método interno para ler arquivos PDF."""
        print(f"  [i] Lendo PDF: {caminho}")
        pdf = PdfReader(caminho)
        return [pagina.extract_text() for pagina in pdf.pages if pagina.extract_text()]
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função LER TXT
    #
    def _ler_txt(self, caminho: str) -> List[str]:
        """Método interno para ler arquivos TXT."""
        print(f"  [i] Lendo TXT: {caminho}")
        with open(caminho, "r", encoding="utf-8") as f:
            return [chunk.strip() for chunk in f.read().split('\n\n') if chunk.strip()]
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função LER DOCX
    #
    def _ler_docx(self, caminho: str) -> List[str]:
        """Método interno para ler arquivos DOCX."""
        print(f"  [i] Lendo DOCX: {caminho}")
        doc = Document(caminho)
        return [paragrafo.text.strip() for paragrafo in doc.paragraphs if paragrafo.text.strip()]
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função CRIAR COLEÇÃO
    #
    def criar_colecao(self, pasta_documentos=PERSIST_PASTA_BIBLIOTECA):
        """Cria a coleção RAG, checando se já existe ou chamando atualizar_colecao."""
        print(f" [i] Iniciando método criar_colecao para coleção: '{self.colecao_nome}'")
        try:
            # Tenta conectar à coleção existente
            self.conectar_colecao()
            print(f" [i] Coleção '{self.colecao_nome}' já existe. Chamando método atualizar_colecao.")
            self.atualizar_colecao(pasta_documentos) # Se existe, atualiza ao invés de recriar do zero
        except ValueError: # ChromaDB ClientError ou ValueError se a coleção não existir
            print(f" [i] Coleção '{self.colecao_nome}' não encontrada. Criando nova coleção.")
            # embedding_fn = EmbeddingFunction() # Usa a classe interna EmbeddingFunction
            print(f"  [i] Criando coleção '{self.colecao_nome}' com embedding dimension: {len(self.embedding_fn(['teste'])[0])}")
            self.colecao = self.client.get_or_create_collection(
                name=self.colecao_nome,
                embedding_function=self.embedding_fn
            )
            print(f"  [i] Dimensão do embedding validada: {len(self.embedding_fn(['teste'])[0])}")

            print(f"  [i] Processando documentos da pasta: '{pasta_documentos}'...")
            for arquivo in os.listdir(pasta_documentos):
                caminho = os.path.join(pasta_documentos, arquivo)
                if os.path.isfile(caminho):
                    try:
                        print(f"   [i] Processando arquivo: {arquivo}")
                        chunks = self._ler_arquivo(caminho)
                        print(f"   [i] Arquivo '{arquivo}' lido e dividido em {len(chunks)} chunks.")
                        for idx, chunk in enumerate(chunks):
                            self.colecao.add(
                                documents=chunk,
                                metadatas={"arquivo": arquivo, "chunk_idx": idx},
                                ids=f"{arquivo}_chunk_{idx}"
                            )
                        print(f"   [+] Adicionado chunks de '{arquivo}' à coleção.")
                        print(f"  [+] Processado: {arquivo} ({len(chunks)} chunks)")
                        
                        # ---------------------------------------------------
                        # Comentando o trecho de mover arquivos para teste
                        # Adicione após o loop de chunks:
                        # self._mover_arquivo(caminho, pasta_documentos)
                        # ---------------------------------------------------
                        
                    except Exception as e:
                        print(f"   [-] Erro em {arquivo}: {str(e)}")
            print(f" [i] Método criar_colecao finalizado. Coleção '{self.colecao_nome}' criada e populada.")
        print(f" [i] Método criar_colecao finalizado.")

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função ZERAR COLEÇÃO
    #
    def zerar_colecao(self):
        """Exclui a coleção RAG atual."""
        print(f" [i] Iniciando método zerar_colecao para coleção: '{self.colecao_nome}'")
        try:
            self.client.delete_collection(name=self.colecao_nome)
            print(f"[!] Coleção '{self.colecao_nome}' zerada")
            self.colecao = None # Reseta self.colecao para None após zerar
            print(f" [i] Método zerar_colecao finalizado.")
            return True
        except Exception as e:
            print(f" [-] Erro ao zerar coleção '{self.colecao_nome}': {str(e)}")
            print(f" [i] Método zerar_colecao finalizado com erro.")
            return False
        
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função atualizar coleção
    #
    def atualizar_colecao(self, pasta_documentos=PERSIST_PASTA_BIBLIOTECA):
        """Atualiza a coleção RAG com novos documentos da pasta."""
        print(f" [i] Iniciando método atualizar_colecao para coleção '{self.colecao_nome}'")
        if not self.colecao:
            print(" [i] Coleção não inicializada, tentando conectar...") # LOG ADICIONADO
            self.conectar_colecao() # Tenta conectar se não estiver conectado ainda

        if not self.colecao: # Verifica novamente se conseguiu conectar ou criar
            print(" [-] Não há coleção conectada para atualizar. Use conectar_colecao() ou criar_colecao() primeiro.")
            return False

        print(f" [i] Processando documentos da pasta para atualização: '{pasta_documentos}'...")
        arquivos_processados_count = 0
        chunks_adicionados_count = 0

        print(f" [i] Coleção atual ANTES da atualização: {self.colecao.count()} documentos.") # LOG ADICIONADO

        for arquivo in os.listdir(pasta_documentos):
            caminho = os.path.join(pasta_documentos, arquivo)
            if os.path.isfile(caminho):
                try:
                    print(f"  [i] Processando arquivo para atualização: {arquivo}")
                    chunks = self._ler_arquivo(caminho)
                    novos_ids = []
                    novos_metadados = []
                    novos_documentos = []

                    for idx, chunk in enumerate(chunks):
                        chunk_id = f"{arquivo}_chunk_{idx}"
                        # Aqui, para uma atualização mais eficiente, você poderia verificar se o chunk_id já existe na coleção
                        # e adicionar apenas se for novo. Por simplicidade, este exemplo apenas adiciona tudo novamente.
                        novos_ids.append(chunk_id)
                        novos_metadados.append({"arquivo": arquivo, "chunk_idx": idx})
                        novos_documentos.append(chunk)

                    if novos_documentos: # Adiciona apenas se houver novos documentos/chunks

                        # ---------------------------------------------------------------------
                        # VERIFICAÇÃO DA DIMENSÃO DO EMBEDDING ANTES DO ADD
                        # embedding_fn_check = EmbeddingFunction() # Instancia EmbeddingFunction LOCALMENTE para verificação
                        assert len(self.embedding_fn(["teste"])[0]) == 768, "Dimensão de embedding inválida!"
                        embedding_dimensao = len(self.embedding_fn([novos_documentos[0]])[0]) if novos_documentos else 0 # Pega a dimensão de um embedding de teste
                        print(f"  [VERIFICAÇÃO] Dimensão do embedding gerado para atualização: {embedding_dimensao}") # Imprime a dimensão
                        if embedding_dimensao != 768: # Alerta se a dimensão estiver errada (opcional, para debug mais visível)
                            print(f"  [ALERTA] Dimensão do embedding NÃO É 768, mas sim {embedding_dimensao}. INESPERADO!")
                        # ---------------------------------------------------------------------


                        self.colecao.add(
                            documents=novos_documentos,
                            metadatas=novos_metadados,
                            ids=novos_ids
                        )
                        chunks_adicionados_count += len(novos_documentos)
                        print(f"  [+] Adicionados {len(novos_documentos)} chunks de '{arquivo}' para atualização.")
                        
                        # ---------------------------------------------------
                        # Comentando o trecho de mover arquivos para teste
                        # Adicione após adicionar os chunks:
                        # self._mover_arquivo(caminho, pasta_documentos)
                        # ---------------------------------------------------
                        
                    arquivos_processados_count += 1
                    print(f" [+] Arquivo atualizado: {arquivo} ({len(chunks)} chunks)")

                except Exception as e:
                    print(f"  [-] Erro ao atualizar arquivo '{arquivo}': {str(e)}")

        print(f" [i] Coleção atual DEPOIS da atualização: {self.colecao.count()} documentos.") # LOG ADICIONADO
        print(f" [i] Método atualizar_colecao finalizado. {arquivos_processados_count} arquivos processados, {chunks_adicionados_count} novos chunks adicionados.")
        return True

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função conectar coleção
    #
    def conectar_colecao(self, nome_colecao=None):
        nome_conectar = nome_colecao or self.colecao_nome
        print(f" [i] Iniciando método conectar_colecao para coleção: '{nome_conectar}'")
        try:
            # Força a redefinição da função de embedding
            self.colecao = self.client.get_or_create_collection(
                name=nome_conectar,
                embedding_function=self.embedding_fn  # Reassocia a função
            )
            self.colecao_nome = nome_conectar
            print(f" [i] Conectado à coleção existente: '{nome_conectar}'.")
            return True
        except Exception as e:
            print(f" [-] Erro: {str(e)}")
            self.colecao = None
            raise ValueError(f"Coleção '{nome_conectar}' não encontrada.")
    
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Função consultar coleção
    #
    def consultar_colecao(self, pergunta, instrucao="", pdf_path=None, imagem_path=None, modelo_de_pensamento="gemini-2.0-flash"):
        """Consulta a coleção RAG e obtém resposta do Gemini."""
        print(f" [i] Iniciando método consultar_colecao. Pergunta: '{pergunta[:50]}...'")
        if not self.colecao:
            self.conectar_colecao() # Tenta conectar se não estiver conectado

        if not self.colecao: # Se ainda não conseguiu conectar, retorna None
            print(" [-] Não há coleção conectada para consultar. Use conectar_colecao() ou criar_colecao() primeiro.")
            return None

        # embedding_fn = EmbeddingFunction() # Instancia EmbeddingFunction para gerar embeddings
        if len(self.embedding_fn([pergunta])[0]) != 768:
            raise ValueError("Dimensão de embedding inválida")

        print(f"  [i] Gerando embedding da pergunta...")
        embedding = self.embedding_fn([pergunta])[0]

        valor_n_results = 3
        print(f"  [i] Consultando ChromaDB (n_results={valor_n_results})...")
        resultados = self.colecao.query(
            query_embeddings=[embedding],
            n_results=valor_n_results
        )

        contextos_recuperados = resultados["documents"][0] if resultados["documents"] else []
        contexto_principal = "\n\n".join(contextos_recuperados)
        print(f"  [i] Contextos recuperados do ChromaDB: {len(contextos_recuperados)}")

        elementos_adicionais = []

        instrucao_completa = (
            "Responda à pergunta a seguir usando **exclusivamente** as informações fornecidas no CONTEXTO fornecido. "
            "**Não use** nenhuma informação externa ou conhecimento prévio. "
            "Se a resposta para a pergunta **não puder ser encontrada** no CONTEXTO, responda de forma concisa: "
            "'Não sei responder com a informação fornecida.' "
            f"{instrucao}"
        )

        if pdf_path and os.path.exists(pdf_path):
            print(f"   [i] Processando PDF adicional: {pdf_path}")
            pdf_texto = self._ler_pdf(pdf_path) # Usa método interno _ler_pdf
            elementos_adicionais.append(f"Conteúdo do PDF Adicional: {' '.join(pdf_texto)}")

        if imagem_path and os.path.exists(imagem_path):
            print(f"   [i] Processando imagem adicional: {imagem_path}")
            imagem = Image.open(imagem_path)
            descricao_imagem = genai.GenerativeModel('gemini-pro-vision').generate_content(imagem).text
            elementos_adicionais.append(f"Descrição da Imagem Adicional: {descricao_imagem}")

        contexto_final = (
            f"{contexto_principal}\n\n"
            f"{'\n\n'.join(elementos_adicionais)}"
            if elementos_adicionais else contexto_principal
        )

        prompt_final = (
            f"Instrução: {instrucao_completa}\n\n"
            f"Pergunta: {pergunta}\n\n"
            f"Contexto:\n{contexto_final}"
        )
        print(f"  [i] Prompt final construído. Enviando para o Gemini...")

        model = genai.GenerativeModel(modelo_de_pensamento)
        resposta_gemini = model.generate_content(prompt_final).text
        print(f"  [i] Resposta do Gemini recebida.")
        print(f" [i] Método consultar_colecao finalizado.")
        return resposta_gemini


#---------------------------------------------------------------------------
# Testar a Classe SistemaRAG
#
testar = False
if testar:
    #----------------------------------------------------------------
    testar_zerar_colecao = False
    if testar_zerar_colecao:
        # Inicializa o sistema RAG
        sistema_rag = SistemaRAG(colecao_nome=PERSIST_COLECAO_NOME, diretorio_persistencia=PERSIST_DIRECTORY) # Você pode mudar o nome da coleção aqui
        # Zera a coleção (opcional, para testes limpos)
        sistema_rag.zerar_colecao()
    #----------------------------------------------------------------
    teste_criar_nova_colecao = False
    if teste_criar_nova_colecao:
        # Inicializa o sistema RAG
        sistema_rag = SistemaRAG(colecao_nome=PERSIST_COLECAO_NOME, diretorio_persistencia=PERSIST_DIRECTORY) # Você pode mudar o nome da coleção aqui
        
        # Zera a coleção (opcional, para testes limpos)
        sistema_rag.zerar_colecao()

        # Cria a coleção (ou atualiza se já existir)
        sistema_rag.criar_colecao(pasta_documentos=PERSIST_PASTA_BIBLIOTECA)

        # # Conecta a uma coleção existente (exemplo) - descomente para testar conectar_colecao
        # sistema_rag.conectar_colecao(nome_colecao="minha_biblioteca_v2") # Conecta a uma coleção específica, se necessário

        # Realiza uma consulta
        interacao_usuario = input("\n Informe o que você quer?   \n")
        resposta = sistema_rag.consultar_colecao(
            pergunta=interacao_usuario,
            instrucao="haja como um grande conhecedor de todos os assuntos do mundo",
            pdf_path="",
            imagem_path="",
            modelo_de_pensamento="gemini-2.0-flash-thinking-exp"
        )

        # Exibe a resposta
        print(" \n Resposta do Gemini: \n" + resposta)
    
    #---------------------------------------------------------------
    testar_atualizar = False
    if testar_atualizar:
        # Inicializa o sistema RAG
        sistema_rag = SistemaRAG(colecao_nome=PERSIST_COLECAO_NOME, diretorio_persistencia=PERSIST_DIRECTORY) # Você pode mudar o nome da coleção aqui
        
        # Atualiza uma coleção no sistema RAG
        sistema_rag.atualizar_colecao(pasta_documentos=PERSIST_PASTA_BIBLIOTECA)
        
        # Realiza uma consulta
        interacao_usuario = input("\n Informe o que você quer?   \n")
        resposta = sistema_rag.consultar_colecao(
            pergunta=interacao_usuario,
            instrucao="haja como um grande conhecedor de todos os assuntos do mundo",
            pdf_path="",
            imagem_path="",
            modelo_de_pensamento="gemini-2.0-flash-thinking-exp"
        )

        # Exibe a resposta
        print(" \n Resposta do Gemini: \n" + resposta)
    #---------------------------------------------------------------
    testar_consultar = False
    if testar_consultar:
        # Inicializa o sistema RAG
        sistema_rag = SistemaRAG(colecao_nome=PERSIST_COLECAO_NOME, diretorio_persistencia=PERSIST_DIRECTORY) # Você pode mudar o nome da coleção aqui
        while testar_consultar:
            # Realiza uma consulta
            interacao_usuario = input("\n Informe o que você quer?   \n")
            resposta = sistema_rag.consultar_colecao(
                pergunta=interacao_usuario,
                instrucao="haja como um grande conhecedor de todos os assuntos do mundo",
                pdf_path="",
                imagem_path="",
                modelo_de_pensamento="gemini-2.0-flash-thinking-exp"
            )

            # Exibe a resposta
            print(" \n Resposta do Gemini: \n" + resposta)
    #---------------------------------------------------------------