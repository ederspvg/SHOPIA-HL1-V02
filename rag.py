import parametros_globais as OneRing
import utilitarios as Canivete
import os
import json # Para persistir a lista de coleções
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
import chromadb
# Removido import não utilizado: from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from PIL import Image
from typing import List, Tuple
import shutil
import pdfplumber

# Configuração da API Gemini
load_dotenv(dotenv_path='ambiente.env')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Configurações do ChromaDB
PERSIST_DIRECTORY = OneRing.PASTA_BANCO # "chroma_db_v13"
PERSIST_PASTA_BIBLIOTECA = OneRing.PASTA_BIBLIOTECA # "biblioteca_geral"
# O nome da coleção antigo não é mais usado da mesma forma
# PERSIST_COLECAO_NOME = OneRing.NOME_COLECAO # "biblioteca_v13"
LISTA_COLECOES_FILE = os.path.join(PERSIST_DIRECTORY, "lista_colecoes.json") # Arquivo para guardar nomes das coleções

# Classe de Embedding compatível com ChromaDB
class EmbeddingFunction:
    def __init__(self):
        # Considerar usar um modelo talvez menor/mais rápido se a performance for um problema,
        # mas 'all-mpnet-base-v2' é um bom padrão.
        self.model = SentenceTransformer('all-mpnet-base-v2')
        # Obter a dimensão do embedding uma vez na inicialização
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f" [i] Embedding model loaded. Dimension: {self.embedding_dim}")

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.model.encode(input).tolist()

class SistemaRAG:
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Classe do Sistema RAG para gerenciamento de coleções e consultas
    # Agora adaptada para múltiplas coleções, uma por documento.
    #
    def __init__(self, diretorio_persistencia=PERSIST_DIRECTORY):
        """Inicializa o Sistema RAG, conectando ao ChromaDB e configurando embedding."""
        print(f" [i] Inicializando SistemaRAG em '{diretorio_persistencia}'")
        self.diretorio_persistencia = diretorio_persistencia
        self.client = chromadb.PersistentClient(path=self.diretorio_persistencia)
        self.embedding_fn = EmbeddingFunction()  # Instância única
        self.lista_nomes_colecoes = self._carregar_lista_colecoes() # Carrega a lista ao iniciar
        print(f" [i] SistemaRAG inicializado. {len(self.lista_nomes_colecoes)} coleções rastreadas.")

    # --- Métodos de Gerenciamento da Lista de Coleções ---

    def _carregar_lista_colecoes(self) -> List[str]:
        """Carrega a lista de nomes de coleções do arquivo JSON."""
        if os.path.exists(LISTA_COLECOES_FILE):
            try:
                with open(LISTA_COLECOES_FILE, 'r', encoding='utf-8') as f:
                    nomes = json.load(f)
                    print(f"  [+] Lista de coleções carregada de '{LISTA_COLECOES_FILE}'.")
                    return nomes
            except Exception as e:
                print(f"  [-] Erro ao carregar lista de coleções: {e}. Iniciando com lista vazia.")
                return []
        else:
            print(f"  [i] Arquivo '{LISTA_COLECOES_FILE}' não encontrado. Iniciando com lista vazia.")
            return []

    def _salvar_lista_colecoes(self):
        """Salva a lista atual de nomes de coleções no arquivo JSON."""
        try:
            os.makedirs(self.diretorio_persistencia, exist_ok=True) # Garante que o diretório existe
            with open(LISTA_COLECOES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.lista_nomes_colecoes, f, ensure_ascii=False, indent=4)
            #print(f"  [+] Lista de {len(self.lista_nomes_colecoes)} coleções salva em '{LISTA_COLECOES_FILE}'.")
        except Exception as e:
            print(f"  [-] Erro ao salvar lista de coleções: {e}")

    # --- Métodos de Leitura de Arquivos (sem alterações significativas) ---

    def _mover_arquivo(self, caminho_arquivo: str, pasta_documentos: str):
        """Move o arquivo processado para a pasta 'lidos'."""
        pasta_lidos = os.path.join(pasta_documentos, "lidos")
        os.makedirs(pasta_lidos, exist_ok=True)
        nome_arquivo = os.path.basename(caminho_arquivo)
        destino = os.path.join(pasta_lidos, nome_arquivo)
        try:
            shutil.move(caminho_arquivo, destino)
            print(f"  [+] Arquivo '{nome_arquivo}' movido para '{pasta_lidos}'.")
        except Exception as e:
            print(f"  [-] Erro ao mover '{nome_arquivo}': {str(e)}")

    def _ler_arquivo(self, caminho: str) -> List[str]:
        """Método interno para ler arquivos."""
        print(f"   [i] Lendo arquivo: {os.path.basename(caminho)}")
        if caminho.endswith(".pdf"):
            return self._ler_pdf_2(caminho)
        elif caminho.endswith(".txt"):
            return self._ler_txt(caminho)
        elif caminho.endswith(".docx"):
            return self._ler_docx(caminho)
        raise ValueError(f"Formato não suportado para {os.path.basename(caminho)}")

    def _ler_pdf_2(self, caminho: str) -> List[str]:
        """Lê PDFs usando pdfplumber, com fallback para PyPDF2."""
        paginas = []
        nome_arquivo_base = os.path.basename(caminho)
        print(f"    [i] Tentando ler '{nome_arquivo_base}' com pdfplumber...")
        try:
            # Tenta com pdfplumber
            with pdfplumber.open(caminho) as pdf:
                for i, pagina in enumerate(pdf.pages):
                    texto = pagina.extract_text()
                    if texto:
                        texto_normalizado = texto.replace('\n', ' ').strip()
                        if texto_normalizado:
                            paginas.append(texto_normalizado)
                    # else: # Log opcional
                    #     print(f"      [d] Página {i+1} (pdfplumber) de '{nome_arquivo_base}' sem texto extraível.")

            if paginas:
                 print(f"    [+] PDF lido com sucesso via pdfplumber: {len(paginas)} páginas com texto.")
                 return paginas
            else:
                 # pdfplumber abriu mas não extraiu texto. Tentar fallback mesmo assim.
                 print(f"    [w] pdfplumber não extraiu texto de '{nome_arquivo_base}'. Tentando fallback com PyPDF2...")
                 # A execução continua para o bloco except Exception (ou fora dele se não houve erro)

        # except pdfplumber.exceptions.PDFSyntaxError as e_syntax: # Exemplo de erro específico
        #     print(f"    [-] Erro de sintaxe PDF (pdfplumber): {e_syntax}. Tentando fallback...")
        except Exception as e_plumber:
            # Captura qualquer erro do pdfplumber, incluindo o "No /Root object!"
            print(f"    [-] Erro ao ler PDF '{nome_arquivo_base}' com pdfplumber: {type(e_plumber).__name__} - {e_plumber}")
            print(f"    [i] Tentando fallback com PyPDF2...")
            # Continua para o código do PyPDF2 abaixo

        # --- Código de Fallback com PyPDF2 ---
        # Só executa se pdfplumber falhou ou não retornou páginas
        if not paginas: # Verifica novamente se já temos páginas (caso pdfplumber não tenha dado erro mas retornado vazio)
            try:
                paginas_pypdf = [] # Usa uma lista separada para o fallback
                with open(caminho, 'rb') as f: # PyPDF2 geralmente prefere modo binário 'rb'
                    reader = PdfReader(f)
                    num_paginas_pypdf = len(reader.pages)
                    # print(f"      [d] PyPDF2 encontrou {num_paginas_pypdf} páginas.") # Debug
                    for i, page in enumerate(reader.pages):
                        try:
                            texto = page.extract_text()
                            if texto:
                                texto_normalizado = texto.replace('\n', ' ').strip()
                                if texto_normalizado:
                                    paginas_pypdf.append(texto_normalizado)
                            # else: # Log opcional
                            #     print(f"      [d] Página {i+1} (PyPDF2) de '{nome_arquivo_base}' sem texto extraível.")
                        except Exception as e_page_extract:
                             print(f"      [-] Erro ao extrair texto da página {i+1} com PyPDF2: {e_page_extract}")
                             continue # Tenta a próxima página

                if paginas_pypdf:
                    print(f"    [+] PDF lido com sucesso via PyPDF2 (fallback): {len(paginas_pypdf)} páginas com texto.")
                    return paginas_pypdf # Retorna o resultado do PyPDF2
                else:
                    print(f"    [-] Fallback com PyPDF2 também não extraiu texto de '{nome_arquivo_base}'.")
                    return [] # Retorna lista vazia se ambos falharem em extrair

            except Exception as e_pypdf:
                # Captura erros específicos do PyPDF2 (incluindo talvez o mesmo 'No /Root object' se for muito corrompido)
                print(f"    [-] Erro ao ler PDF '{nome_arquivo_base}' com PyPDF2 (fallback): {type(e_pypdf).__name__} - {e_pypdf}")
                return [] # Retorna lista vazia se o fallback também der erro

        # Se pdfplumber não deu erro mas retornou vazio, e o fallback não foi tentado ou falhou
        # (Este ponto só é alcançado em cenários muito específicos)
        print(f"    [-] Nenhuma página com texto extraído de '{nome_arquivo_base}' por nenhum método.")
        return []


    def _ler_txt(self, caminho: str) -> List[str]:
        """Lê arquivos TXT e divide em chunks."""
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = self._chunk_text(text)
            print(f"   [+] TXT lido: {len(chunks)} chunks criados.")
            return chunks
        except Exception as e:
            print(f"   [-] Erro ao ler TXT '{os.path.basename(caminho)}': {e}")
            return []

    def _ler_docx(self, caminho: str) -> List[str]:
         """Lê arquivos DOCX, usando parágrafos como chunks."""
         paragrafos = []
         try:
             doc = Document(caminho)
             for paragrafo in doc.paragraphs:
                 texto = paragrafo.text.strip()
                 if texto: # Adiciona apenas parágrafos não vazios
                      paragrafos.append(texto)
             print(f"   [+] DOCX lido: {len(paragrafos)} parágrafos não vazios extraídos.")
             return paragrafos
         except Exception as e:
             print(f"   [-] Erro ao ler DOCX '{os.path.basename(caminho)}': {e}")
             return []

    def _chunk_text(self, text: str) -> List[str]:
        """Divide texto (geralmente de TXT) em chunks por linha dupla."""
        if not text or text.strip() == "":
            return []
        # Divide por quebras de linha dupla e remove espaços extras
        chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
        return chunks

    # --- Métodos Principais de Gerenciamento das Coleções ---

    def _limpar_colecoes_existentes(self):
        """Deleta todas as coleções listadas em self.lista_nomes_colecoes."""
        if not self.lista_nomes_colecoes:
            print("  [i] Nenhuma coleção existente para limpar.")
            return

        print(f" [!] Limpando {len(self.lista_nomes_colecoes)} coleções existentes...")
        nomes_apagados = []
        nomes_falhados = []
        for nome_colecao in self.lista_nomes_colecoes:
            try:
                self.client.delete_collection(name=nome_colecao)
                print(f"   [+] Coleção '{nome_colecao}' deletada.")
                nomes_apagados.append(nome_colecao)
            except Exception as e:
                # Pode acontecer se o arquivo de lista estiver dessincronizado com o DB
                print(f"   [-] Erro ao deletar coleção '{nome_colecao}': {e}. Pode já não existir.")
                nomes_falhados.append(nome_colecao)

        # Atualiza a lista interna apenas com os que falharam (se houver)
        self.lista_nomes_colecoes = nomes_falhados
        self._salvar_lista_colecoes() # Salva a lista (agora vazia ou com falhas)
        print(f" [!] Limpeza concluída. {len(nomes_apagados)} coleções deletadas.")


    def adicionar_documento_incremental(self, caminho_arquivo: str):
        """
        Adiciona um único documento criando uma NOVA coleção com o próximo número sequencial disponível,
        sem apagar ou modificar as coleções existentes.

        Args:
            caminho_arquivo (str): O caminho completo para o arquivo a ser adicionado.

        Returns:
            bool: True se o documento foi adicionado com sucesso, False caso contrário.
        """
        print(f"\n [>] Adicionando documento incrementalmente: {os.path.basename(caminho_arquivo)}")
        if not os.path.exists(caminho_arquivo) or not os.path.isfile(caminho_arquivo):
            print(f"   [-] Erro: Arquivo não encontrado em '{caminho_arquivo}'.")
            return False

        nome_arquivo = os.path.basename(caminho_arquivo)

        # --- Determinar o próximo nome de coleção numérico ---
        numeros_existentes = []
        if self.lista_nomes_colecoes:
            for nome_col in self.lista_nomes_colecoes:
                try:
                    # Assume que os nomes são strings numéricas como "0001", "0020"
                    num = int(nome_col)
                    numeros_existentes.append(num)
                except ValueError:
                    print(f"   [w] Aviso: Nome de coleção não numérico encontrado na lista: '{nome_col}'. Será ignorado para determinar o próximo número.")
                    # Você pode decidir como tratar isso - aqui estamos apenas ignorando
                    continue # Pula para o próximo nome na lista

        proximo_numero = max(numeros_existentes) + 1 if numeros_existentes else 1
        # Formata o número com zeros à esquerda (ex: 4 dígitos)
        # Ajuste o '04d' se precisar de mais ou menos dígitos
        nome_nova_colecao = f"{proximo_numero:04d}"
        print(f"   [i] Próximo número de coleção determinado: {nome_nova_colecao}")
        # --- Fim da determinação do nome ---

        # Verificar se, por algum motivo, essa coleção já existe no DB (embora não devesse se a lógica estiver correta)
        try:
             # Usamos get_collection para verificar se existe. Se não existir, ele levanta uma exceção.
             self.client.get_collection(name=nome_nova_colecao)
             # Se chegou aqui, a coleção JÁ EXISTE, o que é inesperado.
             print(f"   [-] Erro Inesperado: A coleção '{nome_nova_colecao}' já existe no banco de dados, embora não devesse. Verifique a lista '{LISTA_COLECOES_FILE}' e o estado do banco. Adição cancelada.")
             return False
        except Exception as e:
             # É esperado que a coleção não exista, então uma exceção aqui (geralmente relacionada a não encontrar) é normal.
             # print(f"   [d] Verificação de existência da coleção '{nome_nova_colecao}' passou (não encontrada, como esperado).")
             pass # Continua o processo


        # Processar e adicionar o novo arquivo
        try:
            chunks = self._ler_arquivo(caminho_arquivo)
            if not chunks:
                print(f"   [w] Nenhum chunk de texto válido extraído de '{nome_arquivo}'. Adição cancelada.")
                return False

            print(f"   [i] Criando nova coleção '{nome_nova_colecao}' para o arquivo '{nome_arquivo}'...")
            # Usamos get_or_create_collection para criar a coleção que sabemos que não existe (baseado na verificação acima)
            colecao_atual = self.client.get_or_create_collection(
                name=nome_nova_colecao,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine", "original_filename": nome_arquivo} # Guarda nome original
            )

            ids_chunks = []
            metadados_chunks = []
            documentos_chunks = []
            chunks_validos = 0

            for idx, chunk in enumerate(chunks):
                if not chunk or not chunk.strip(): continue
                # Usar o nome da NOVA coleção no ID do chunk
                chunk_id = f"{nome_nova_colecao}_chunk_{idx}"
                ids_chunks.append(chunk_id)
                # Armazena o nome do arquivo original no metadado do chunk
                metadados_chunks.append({"arquivo_origem": nome_arquivo, "chunk_index": idx})
                documentos_chunks.append(chunk)
                chunks_validos += 1

            if documentos_chunks:
                colecao_atual.add(
                    documents=documentos_chunks,
                    metadatas=metadados_chunks,
                    ids=ids_chunks
                )
                print(f"   [+] Adicionados {chunks_validos} chunks válidos à NOVA coleção '{nome_nova_colecao}'.")

                # Adiciona o nome da nova coleção à lista em memória
                self.lista_nomes_colecoes.append(nome_nova_colecao)
                # Salva a lista atualizada no arquivo JSON
                self._salvar_lista_colecoes()
                print(f"   [+] Coleção '{nome_nova_colecao}' adicionada à lista de rastreamento e salva.")

                # Opcional: Mover o arquivo processado para a pasta 'lidos'
                # self._mover_arquivo(caminho_arquivo, os.path.dirname(caminho_arquivo))
                return True
            else:
                # Se não havia chunks válidos, a coleção foi criada vazia. Removemos ela.
                print(f"   [w] Nenhum chunk válido encontrado após leitura. A coleção '{nome_nova_colecao}' foi criada vazia e será removida.")
                try:
                    self.client.delete_collection(name=nome_nova_colecao)
                    print(f"   [i] Coleção vazia '{nome_nova_colecao}' deletada.")
                except Exception as del_e:
                    print(f"   [-] Erro ao tentar deletar coleção vazia '{nome_nova_colecao}': {del_e}")
                # Não adicionamos à lista e retornamos False
                return False

        except Exception as e:
            print(f"   [-] ERRO GERAL ao adicionar incrementalmente o arquivo '{nome_arquivo}' para a coleção '{nome_nova_colecao}': {e}")
            # Tenta limpar a coleção que pode ter sido criada parcialmente
            try:
                 self.client.delete_collection(name=nome_nova_colecao)
                 print(f"   [i] Tentativa de limpeza da coleção '{nome_nova_colecao}' após erro.")
                 # Não modifica a lista self.lista_nomes_colecoes pois a operação falhou
            except Exception:
                 print(f"   [w] Aviso: Falha ao tentar limpar a coleção '{nome_nova_colecao}' após erro.")
            return False
    
    def criar_colecoes(self, pasta_documentos=PERSIST_PASTA_BIBLIOTECA):
        """
        Recria as coleções: deleta todas as existentes listadas e cria uma
        nova coleção para cada arquivo encontrado na pasta_documentos.
        """
        print(f" [i] Iniciando método criar_colecoes...")
        print(f" [i] Pasta de documentos: '{pasta_documentos}'")

        # 1. Limpar coleções antigas e a lista
        self._limpar_colecoes_existentes() # Isso também salva a lista vazia

        # 2. Iterar sobre os arquivos, criar coleção e adicionar dados
        contador_colecao = 0
        arquivos_processados = 0
        arquivos_com_erro = 0
        novos_nomes_colecoes = []

        arquivos_na_pasta = [f for f in os.listdir(pasta_documentos) if os.path.isfile(os.path.join(pasta_documentos, f))]
        print(f" [i] Encontrados {len(arquivos_na_pasta)} arquivos em '{pasta_documentos}'.")


        for nome_arquivo in arquivos_na_pasta:
            caminho_arquivo = os.path.join(pasta_documentos, nome_arquivo)
            print(f"\n [>] Processando arquivo: {nome_arquivo}")
            try:
                # Ler os chunks do arquivo
                chunks = self._ler_arquivo(caminho_arquivo)
                if not chunks:
                    print(f"   [w] Nenhum chunk de texto válido extraído de '{nome_arquivo}'. Pulando.")
                    # Opcional: mover para uma pasta de 'erros' ou 'vazios'
                    # self._mover_arquivo(caminho_arquivo, os.path.join(pasta_documentos, 'vazios'))
                    continue # Pula para o próximo arquivo

                # Gerar nome numérico para a coleção
                contador_colecao += 1
                nome_nova_colecao = f"{contador_colecao:04d}" # Ex: 0001, 0002, ...

                print(f"   [i] Criando coleção '{nome_nova_colecao}' para '{nome_arquivo}'...")

                # Criar a coleção específica para este documento
                colecao_atual = self.client.get_or_create_collection(
                    name=nome_nova_colecao,
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine"} # Opcional: especificar métrica de distância
                )

                # Preparar dados para adição em lote
                ids_chunks = []
                metadados_chunks = []
                documentos_chunks = []
                chunks_validos = 0

                for idx, chunk in enumerate(chunks):
                    if not chunk or not chunk.strip():
                        # print(f"    [-] Chunk {idx} vazio em '{nome_arquivo}'. Pulando.")
                        continue

                    # Validação da dimensão do embedding (opcional, mas bom para debug)
                    # embedding_teste = self.embedding_fn([chunk])[0]
                    # if len(embedding_teste) != self.embedding_fn.embedding_dim:
                    #     print(f"    [-] Dimensão de embedding inválida ({len(embedding_teste)}) para chunk {idx} de '{nome_arquivo}'. Pulando.")
                    #     continue

                    chunk_id = f"{nome_arquivo}_chunk_{idx}"
                    ids_chunks.append(chunk_id)
                    metadados_chunks.append({"arquivo_origem": nome_arquivo, "chunk_index": idx})
                    documentos_chunks.append(chunk)
                    chunks_validos += 1

                # Adicionar chunks válidos à coleção específica
                if documentos_chunks:
                    colecao_atual.add(
                        documents=documentos_chunks,
                        metadatas=metadados_chunks,
                        ids=ids_chunks
                    )
                    print(f"   [+] Adicionados {chunks_validos} chunks válidos à coleção '{nome_nova_colecao}'.")
                    novos_nomes_colecoes.append(nome_nova_colecao) # Adiciona à lista de sucesso
                    arquivos_processados += 1
                    # Mover arquivo após processamento bem-sucedido (opcional)
                    # self._mover_arquivo(caminho_arquivo, pasta_documentos)
                else:
                     print(f"   [w] Nenhum chunk válido para adicionar à coleção para o arquivo '{nome_arquivo}'. A coleção '{nome_nova_colecao}' foi criada mas está vazia.")
                     # Opcional: Deletar a coleção vazia recém-criada
                     try:
                         self.client.delete_collection(name=nome_nova_colecao)
                         print(f"   [i] Coleção vazia '{nome_nova_colecao}' deletada.")
                     except Exception as del_e:
                         print(f"   [-] Erro ao deletar coleção vazia '{nome_nova_colecao}': {del_e}")


            except Exception as e:
                print(f"   [-] ERRO GERAL ao processar o arquivo '{nome_arquivo}': {e}")
                arquivos_com_erro += 1
                # Opcional: mover para pasta de 'erros'
                # self._mover_arquivo(caminho_arquivo, os.path.join(pasta_documentos, 'erros'))

        # 3. Atualizar a lista de nomes de coleções e salvar
        self.lista_nomes_colecoes = novos_nomes_colecoes
        self._salvar_lista_colecoes()

        print(f"\n [i] Método criar_colecoes finalizado.")
        print(f"   - {arquivos_processados} arquivos processados com sucesso.")
        print(f"   - {len(self.lista_nomes_colecoes)} coleções criadas e rastreadas.")
        print(f"   - {arquivos_com_erro} arquivos falharam no processamento.")
        return True

    def zerar_todas_colecoes(self):
        """Exclui todas as coleções RAG rastreadas."""
        print(f" [i] Iniciando método zerar_todas_colecoes...")
        self._limpar_colecoes_existentes() # Reutiliza a lógica de limpeza
        # Garante que o arquivo de lista seja removido também
        if os.path.exists(LISTA_COLECOES_FILE):
            try:
                os.remove(LISTA_COLECOES_FILE)
                print(f"  [+] Arquivo de lista '{LISTA_COLECOES_FILE}' removido.")
            except Exception as e:
                print(f"  [-] Erro ao remover arquivo de lista '{LISTA_COLECOES_FILE}': {e}")
        self.lista_nomes_colecoes = [] # Garante que a lista em memória está vazia
        print(f" [i] Todas as coleções rastreadas foram zeradas.")
        return True

    def atualizar_colecoes(self, pasta_documentos=PERSIST_PASTA_BIBLIOTECA):
        """
        Atualiza as coleções. Na abordagem 'uma coleção por arquivo',
        isso equivale a recriar tudo do zero baseado nos arquivos atuais da pasta.
        """
        print(f" [i] Iniciando método atualizar_colecoes...")
        print(f" [i] Redirecionando para criar_colecoes para garantir consistência.")
        return self.criar_colecoes(pasta_documentos)


    def consultar_multiplas_colecoes(self,
                                 pergunta: str,
                                 instrucao: str = "",
                                 pdf_path: str = None,
                                 imagem_path: str = None,
                                 modelo_de_pensamento: str = "gemini-1.5-flash",
                                 n_results_per_colecao: int = 5, # Nº inicial de chunks a buscar por coleção
                                 max_distance_threshold: float = 0.8 # NOVO: Limiar MÁXIMO de distância (menor = mais similar). Ajuste este valor!
                                 ) -> str:
        """
        Consulta coleções, recupera chunks com distâncias, filtra por um
        limiar de distância MÁXIMA (max_distance_threshold) e usa apenas os
        chunks relevantes no contexto do LLM.
        IMPORTANTE: Requer que as coleções tenham sido criadas com métrica 'cosine'.
        """
        print(f"\n [i] Iniciando consulta com filtro de relevância...")
        print(f"   Pergunta (início): '{pergunta[:70]}...'")
        print(f"   Pergunta Completa (início): '{pergunta}...'")
        print(f"   Configuração: {n_results_per_colecao} resultados/coleção, Limiar Distância Máx: {max_distance_threshold}")

        if not self.lista_nomes_colecoes:
            print(" [-] Nenhuma coleção RAG encontrada para consultar.")
            return "Não há base de conhecimento carregada para consultar."

        print(f"  [i] Consultando {len(self.lista_nomes_colecoes)} coleções...")

        try:
            embedding_pergunta = self.embedding_fn([pergunta])[0]
            if len(embedding_pergunta) != self.embedding_fn.embedding_dim:
                raise ValueError(f"Dimensão de embedding da pergunta inválida: {len(embedding_pergunta)}")
        except Exception as e:
            print(f"  [-] Erro ao gerar embedding para a pergunta: {e}")
            return "Erro ao processar a pergunta."

        # Lista para armazenar APENAS os chunks que passam no limiar
        contextos_relevantes_filtrados: List[str] = []
        debug_info_chunks: List[Tuple[float, str, dict]] = [] # Para análise
        colecoes_consultadas = 0
        erros_consulta = 0
        chunks_recuperados_total = 0
        chunks_passaram_filtro = 0

        for nome_colecao in self.lista_nomes_colecoes:
            try:
                colecao = self.client.get_collection(
                    name=nome_colecao,
                    embedding_function=self.embedding_fn
                )

                # Recupera documentos, distâncias e metadados
                resultados = colecao.query(
                    query_embeddings=[embedding_pergunta],
                    n_results=n_results_per_colecao, # Pega K resultados iniciais
                    include=['documents', 'distances', 'metadatas']
                )

                documentos = resultados.get("documents", [[]])[0]
                distancias = resultados.get("distances", [[]])[0]
                metadados = resultados.get("metadatas", [[]])[0]

                chunks_recuperados_total += len(documentos)

                # --- FILTRAGEM POR LIMIAR DE DISTÂNCIA ---
                for dist, doc, meta in zip(distancias, documentos, metadados):
                    # Armazena para debug ANTES de filtrar
                    debug_info_chunks.append((dist, doc, meta))

                    # Verifica se o chunk é válido e se a distância está DENTRO do limiar aceitável
                    # Para 'cosine' space no ChromaDB, distância menor é melhor (0 = idêntico)
                    if doc and doc.strip() and dist <= max_distance_threshold:
                        # Chunk passou no teste de relevância!
                        arquivo_origem = meta.get('arquivo_origem', 'Desconhecido')
                        # Adiciona o chunk formatado à lista final
                        contextos_relevantes_filtrados.append(f"Fonte: {arquivo_origem}\n{doc}")
                        chunks_passaram_filtro += 1
                    # else: # Opcional: Logar chunks descartados
                    #     if doc and doc.strip():
                    #          print(f"      [!] Chunk descartado (Dist: {dist:.4f} > {max_distance_threshold}): '{doc[:80]}...'")

                colecoes_consultadas += 1

            except Exception as e:
                print(f"   [-] Erro ao consultar coleção '{nome_colecao}': {e}")
                erros_consulta += 1

        print(f"  [i] Consulta inicial concluída em {colecoes_consultadas} coleções ({erros_consulta} erros).")
        print(f"  [i] Total de chunks recuperados inicialmente: {chunks_recuperados_total}")
        print(f"  [i] Total de chunks que passaram no filtro (Dist <= {max_distance_threshold}): {chunks_passaram_filtro}")

        # --- DEBUG ADICIONAL: Mostrar os chunks recuperados antes do filtro ---
        # Ordena para facilitar a visualização dos melhores recuperados, mesmo que filtrados depois
        debug_info_chunks.sort(key=lambda item: item[0])
        print(f"\n   --- DEBUG: Top {min(15, len(debug_info_chunks))} Chunks Recuperados (Antes do Filtro de Distância) ---")
        for i, (dist, doc, meta) in enumerate(debug_info_chunks[:15]): # Mostra os 15 melhores recuperados
            passou_no_filtro = "SIM" if dist <= max_distance_threshold else "NAO"
            arquivo_origem = meta.get('arquivo_origem', 'Desconhecido')
            print(f"     Rank {i+1}: Dist={dist:.4f} (Filtro: {passou_no_filtro}) | Fonte: {arquivo_origem} | Texto: '{doc[:100]}...'")
        print("   --- FIM DEBUG ---")
        # ---------------------------------------------------------------------


        if not contextos_relevantes_filtrados:
            print("  [w] Nenhum contexto relevante encontrado que atenda ao limiar de distância.")
            # Decide o que fazer: retornar mensagem ou enviar prompt vazio/padrão para o LLM
            contexto_principal = "Nenhuma informação relevante encontrada na base de conhecimento que atenda aos critérios de similaridade."
            # Alternativamente, poderia tentar relaxar o threshold aqui ou ter outra estratégia de fallback
        else:
            # Junta os chunks que passaram pelo filtro
            contexto_principal = "\n\n---\n\n".join(contextos_relevantes_filtrados)

            # Opcional: Contagem de Tokens
            # try:
            #     encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            #     num_tokens = len(encoding.encode(contexto_principal))
            #     print(f"   [i] Estimativa de tokens no contexto filtrado: {num_tokens}")
            # except Exception as enc_e:
            #     print(f"   [w] Não foi possível estimar tokens: {enc_e}")


        # --- Lógica para adicionar PDF/Imagem e chamar Gemini (Permanece igual) ---
        elementos_adicionais = []
        instrucao_completa = (
            "Responda à pergunta a seguir usando **exclusivamente** as informações fornecidas no CONTEXTO. "
            "**Não use** nenhuma informação externa ou conhecimento prévio. "
            "Se a resposta para a pergunta **não puder ser encontrada** no CONTEXTO, responda de forma concisa: "
            "'Não sei responder com a informação fornecida.' "
            f"{instrucao}"
        )

        if pdf_path and os.path.exists(pdf_path):
            print(f"   [i] Processando PDF adicional: {pdf_path}")
            pdf_texto_chunks = self._ler_pdf_2(pdf_path)
            if pdf_texto_chunks:
                elementos_adicionais.append(f"Conteúdo do PDF Adicional: {' '.join(pdf_texto_chunks)}")

        if imagem_path and os.path.exists(imagem_path):
            print(f"   [i] Processando imagem adicional: {imagem_path}")
            try:
                imagem = Image.open(imagem_path)
                vision_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = vision_model.generate_content(["Descreva esta imagem com o máximo de detalhes e transcreva todo o texto presente na imagem para posterior análise.", imagem])
                descricao_imagem = response.text
                elementos_adicionais.append(f"Descrição da Imagem Adicional: {descricao_imagem}")
            except Exception as e:
                print(f"   [-] Erro ao processar imagem adicional: {e}")

        contexto_final = contexto_principal
        if elementos_adicionais:
            contexto_final += "\n\n---\n\n" + "\n\n".join(elementos_adicionais)

        prompt_final = (
            f"Instrução: {instrucao_completa}\n\n"
            f"Contexto:\n{contexto_final}\n\n"
            f"Pergunta: {pergunta}"
        )

        try:
            Canivete.salvar_txt(contexto_final, 'contexto_final.txt')
        except Exception as save_e:
            print(f"   [-] Erro ao salvar contexto final: {save_e}")

        print(f"  [i] Enviando prompt para o modelo Gemini ('{modelo_de_pensamento}')...")

        #-----------------------------------------------------------------------
        # Para imprimir a lista de modelos disponíveis (opcional)
        logic_lista_modelos = True # Para depuração, se necessário
        if logic_lista_modelos:
            # listar modelos
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(m.name)
            #
        #-----------------------------------------------------------------------
        
        try:
            model = genai.GenerativeModel(modelo_de_pensamento)
            resposta_gemini = model.generate_content(prompt_final).text
            print(f"  [+] Resposta do Gemini recebida.")
        except Exception as e:
            print(f"  [-] Erro ao chamar a API Gemini: {e}")
            error_message = str(e)
            if hasattr(e, 'message'): error_message = e.message
            if "block_reason: SAFETY" in error_message or "response was blocked" in error_message:
                resposta_gemini = "A resposta foi bloqueada devido às configurações de segurança..."
            elif "token" in error_message.lower():
                resposta_gemini = f"Ocorreu um erro relacionado ao limite de tokens: {error_message}"
            else:
                resposta_gemini = f"Ocorreu um erro ao gerar a resposta pela API: {error_message}"

        print(f" [i] Método consultar_multiplas_colecoes finalizado. \n {resposta_gemini} \n")
        return resposta_gemini


#---------------------------------------------------------------------------
# Bloco de Teste Adaptado
#---------------------------------------------------------------------------
if __name__ == "__main__": # Boa prática para execução de script

    # --- Teste 1: Zerar e Criar Coleções ---
    executar_teste_criar = True #False
    if executar_teste_criar:
        print("\n--- INICIANDO TESTE: ZERAR E CRIAR COLEÇÕES ---")
        # Inicializa o sistema RAG (carrega lista existente, se houver)
        sistema_rag = SistemaRAG(diretorio_persistencia=PERSIST_DIRECTORY)

        # Zera TUDO antes de criar (para garantir um estado limpo)
        print("\n[PASSO 1] Zerando coleções existentes...")
        sistema_rag.zerar_todas_colecoes()

        # Cria as novas coleções (uma para cada arquivo)
        print("\n[PASSO 2] Criando novas coleções a partir da pasta...")
        sistema_rag.criar_colecoes(pasta_documentos=PERSIST_PASTA_BIBLIOTECA)

        print("\n--- TESTE ZERAR/CRIAR CONCLUÍDO ---")
        print(f"   Coleções ativas rastreadas: {sistema_rag.lista_nomes_colecoes}")

    # --- Teste 1.5: Adicionar Documento Incremental ---
    executar_teste_add_incremental = False # Defina como True para rodar este passo
    if executar_teste_add_incremental:
        print("\n--- INICIANDO TESTE: ADICIONAR DOCUMENTO INCREMENTAL ---")
        sistema_rag_add = SistemaRAG(diretorio_persistencia=PERSIST_DIRECTORY) # Carrega estado atual
        print(f"   Coleções ANTES da adição: {sistema_rag_add.lista_nomes_colecoes}")

        # Crie um arquivo temporário para adicionar (ou use um arquivo real)
        # IMPORTANTE: Coloque este arquivo em um local ACESSÍVEL, não necessariamente na pasta principal da biblioteca
        #             pois a função _mover_arquivo (se ativada) pode movê-lo.
        pasta_origem_novo_arquivo = 'biblioteca_geral' # Pasta atual, ou especifique outra
        nome_novo_arquivo = 'Manual WFLUFT10 - Resolução de Problemas na Importação de CTE do Informa para o Protheus.pdf'
        
        caminho_novo_arquivo = os.path.join(pasta_origem_novo_arquivo, nome_novo_arquivo)

        print(f"\n[PASSO 3] Adicionando incrementalmente o arquivo '{nome_novo_arquivo}'...")
        sucesso_add = sistema_rag_add.adicionar_documento_incremental(caminho_novo_arquivo)

        if sucesso_add:
            print(f"   Coleções DEPOIS da adição: {sistema_rag_add.lista_nomes_colecoes}")
            # Opcional: Limpar o arquivo de teste criado
            # try:
            #     os.remove(caminho_novo_arquivo)
            #     print(f"   [i] Arquivo de teste '{nome_novo_arquivo}' removido.")
            # except OSError as e:
            #     print(f"   [w] Não foi possível remover o arquivo de teste '{nome_novo_arquivo}': {e}")
        else:
            print(f"   [!] Falha ao adicionar o documento incrementalmente.")
            print(f"   Coleções após tentativa falha: {sistema_rag_add.lista_nomes_colecoes}")


        print("\n--- TESTE ADICIONAR INCREMENTAL CONCLUÍDO ---")
    
    # --- Teste 2: Consultar as Coleções Criadas ---
    executar_teste_consultar = True #False
    if executar_teste_consultar:
        print("\n--- INICIANDO TESTE: CONSULTAR COLEÇÕES ---")
        # Re-inicializa para simular uma nova execução ou continua com o objeto existente
        # Se recriar o objeto, ele deve carregar a lista salva no teste anterior
        sistema_rag_consulta = SistemaRAG(diretorio_persistencia=PERSIST_DIRECTORY)

        if not sistema_rag_consulta.lista_nomes_colecoes:
             print("\n[!] Não há coleções rastreadas para consultar. Execute o teste de criação primeiro.")
        else:
            print(f"\n[i] Sistema pronto para consulta com {len(sistema_rag_consulta.lista_nomes_colecoes)} coleções.")
            while True:
                try:
                    interacao_usuario = input("\nFaça sua pergunta (ou digite 'sair' para terminar): \n -> ")
                    if interacao_usuario.lower() == 'sair':
                        break

                    resposta = sistema_rag_consulta.consultar_multiplas_colecoes(
                        pergunta=interacao_usuario,
                        instrucao="Haja como um especialista nos assuntos questionados e responda de forma clara, detalhada e ao mesmo tempo didática.", # Instrução adicional opcional
                        # pdf_path="caminho/para/um/pdf_extra.pdf", # Exemplo
                        # imagem_path="caminho/para/uma/imagem_extra.png", # Exemplo
                        modelo_de_pensamento="gemini-2.0-flash-thinking-exp", # Modelo mais recente e geralmente bom
                        n_results_per_colecao=10, # Quantos chunks buscar por *cada* coleção/documento
                        max_distance_threshold=0.8 # Limiar de distância máxima para filtrar os chunks recuperados
                    )

                    print(f"\n--- Resposta --- \n{resposta}\n---------------")

                except KeyboardInterrupt:
                    print("\nConsulta interrompida pelo usuário.")
                    break
                except Exception as e:
                    print(f"\n[!] Ocorreu um erro durante a consulta: {e}")

        print("\n--- TESTE CONSULTAR CONCLUÍDO ---")
