from imports import *
logging.getLogger("pdfminer").setLevel(logging.ERROR)

PASTA_PDFS = r"C:\\Users\\aesouza\\Desktop\\diario_ofc"
PASTA_DESTINO = r"C:\\Users\\aesouza\\Desktop\\diario_mes"

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1"
)

def consultar_llm(prompt):
    try:
        resposta = client.chat.completions.create(
            model="llama3.1:8b",
            messages=[
                {"role": "system", "content":
                    """Você é um especialista em atos administrativos do Diário Oficial.
                    Sua tarefa é analisar o texto abaixo e identificar exclusivamente os seguintes atos:
                    - Nomeações para cargos em comissão.
                    - Exonerações, desligamentos ou declarações de vacância (ex: exonerado, exonerada, fica exonerado, desligado, declara vago, vacância).
                    - Atos de "Tornar sem efeito" que anulam nomeações ou exonerações.

                    Ignore qualquer outro conteúdo, como nomeações para conselhos, comissões, grupos de trabalho ou funções gratificadas que não sejam cargos em comissão.
                    Para cada ato que corresponda estritamente aos critérios, retorne no seguinte formato, com um ato por linha:
                    Nome: [NOME COMPLETO] - Secretaria: [SECRETARIA] - Ato: [NOMEAÇÃO | EXONERAÇÃO | TORNAR SEM EFEITO]
                    
                    Se a secretaria não for explicitamente mencionada, use "não informada".
                    Se nenhum ato correspondente for encontrado no texto, não retorne NADA."""
                },
                {"role": "user", "content": f"Texto para análise:\n{prompt}"}
            ],
            temperature=0.0,
        )
        return resposta.choices[0].message.content
    except Exception as e:
        return f"Erro ao consultar LLM local: {e}"

def mover_arquivos_pasta(pasta_origem, pasta_destino):
    if not os.path.exists(pasta_origem):
        print(f"A pasta '{pasta_origem}' não existe.")
        return
    
    os.makedirs(pasta_destino, exist_ok=True)

    for arquivo in os.listdir(pasta_origem):
        caminho_origem = os.path.join(pasta_origem, arquivo)
        caminho_destino = os.path.join(pasta_destino, arquivo)
        try:
            if os.path.isfile(caminho_origem) or os.path.isdir(caminho_origem):
                shutil.move(caminho_origem, caminho_destino)
                print(f"Movido: {arquivo}")
        except Exception as e:
            print(f"Erro ao mover {caminho_origem}: {e}")

def extrair_texto_pdf(caminho_pdf):
    """
    Extrai o texto de um PDF, retornando uma lista onde cada item é o texto de uma página.
    """
    textos_das_paginas = []
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                texto_da_pagina = page.extract_text(x_tolerance=2)
                if texto_da_pagina:
                    textos_das_paginas.append(texto_da_pagina)
    except Exception as e:
        print(f"Erro ao ler o PDF {caminho_pdf}: {e}")
    return textos_das_paginas



def dividir_por_artigos_relevantes(texto, tabelas):
    """
    Divide o texto por artigos de forma mais robusta, mantendo o conteúdo completo de cada artigo.
    """
    artigos_filtrados = []
    # Padrão para encontrar "Art. X" ou "Artigo X"
    padrao_artigo = r"(?=Art(?:igo)?\.?\s*\d+[ºo]?\.?)"
    
    # Encontra os inícios de todos os artigos
    indices = [m.start() for m in re.finditer(padrao_artigo, texto, re.IGNORECASE)]
    
    # Se nenhum artigo for encontrado, mas houver palavras-chave, processa o texto inteiro
    if not indices and re.search(r"\b(exoner|nomead|TORNA SEM EFEITO)", texto, re.IGNORECASE):
        return [texto]

    # Cria os trechos de cada artigo
    trechos = [texto[indices[i]:indices[i+1]] for i in range(len(indices)-1)]
    if indices:
        trechos.append(texto[indices[-1]:])

    for trecho in trechos:
        # Filtra apenas os trechos que contêm os atos de interesse
        if re.search(r"\b(exoner|nomead|TORNA SEM EFEITO)[a-z]*[ãa]?[oõ]?\b", trecho, re.IGNORECASE):
            artigos_filtrados.append(trecho.strip())

    return artigos_filtrados


def processar_diarios_com_llm(pasta_pdfs=PASTA_PDFS):
    """
    Processa todos os PDFs em uma pasta, analisando-os página por página para
    encontrar atos de nomeação e exoneração usando um LLM.
    """
    resultados_finais = []
    for arquivo in os.listdir(pasta_pdfs):
        if not arquivo.lower().endswith(".pdf"):
            continue

        caminho_completo = os.path.join(pasta_pdfs, arquivo)
        print(f"Processando: {arquivo}")
        
        textos_por_pagina = extrair_texto_pdf(caminho_completo)
        respostas_do_arquivo = []

        for i, texto_pagina in enumerate(textos_por_pagina):
            # Verifica a presença de palavras-chave para evitar chamadas desnecessárias ao LLM
            if re.search(r"\b(exoner|nomead|torna sem efeito)", texto_pagina, re.IGNORECASE):
                print(f"  -> Página {i+1} parece relevante. Enviando para análise...")
                resposta_llm = consultar_llm(texto_pagina)
                
                # Processa a resposta do LLM, que pode ter múltiplas linhas
                if resposta_llm and "Erro ao consultar" not in resposta_llm:
                    linhas_limpas = [linha.strip() for linha in resposta_llm.split('\n') if linha.strip()]
                    if linhas_limpas:
                        respostas_do_arquivo.extend(linhas_limpas)

        # Formata o resultado final para o arquivo processado
        if respostas_do_arquivo:
            resultado_formatado = f"{arquivo}\n" + "\n".join(respostas_do_arquivo)
            print(f"Resultado para {arquivo}:\n" + "\n".join(respostas_do_arquivo))
        else:
            resultado_formatado = f"{arquivo}\nNenhum ato relevante encontrado."
            print(f"Resultado para {arquivo}: Nenhum ato relevante encontrado.")
        
        resultados_finais.append(resultado_formatado)
        
    return resultados_finais


def download_pdf_requests(edicoes, pasta_destino, max_tentativas=3, intervalo=5):
    data = (datetime.now() - timedelta(days=1)).strftime('%Y_%m_%d')
    if datetime.today().strftime("%A") == "Monday":
        data = (datetime.now() - timedelta(days=3)).strftime('%Y_%m_%d')
    # data = '2025_05_06'

    for edicao in edicoes:
        url = f"https://diof.io.org.br/api/diario-oficial/download/{data}{edicao}004611.pdf"
        destino = os.path.join(pasta_destino, f"{data}{edicao}004611.pdf")
        
        tentativas = 0
        sucesso = False

        while tentativas < max_tentativas and not sucesso:
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()

                with open(destino, "wb") as f:
                    f.write(response.content)
                print(f"PDF baixado: {destino}")
                sucesso = True

            except requests.exceptions.Timeout:
                print(f"Timeout ao tentar baixar: {url}")
            except requests.exceptions.ConnectionError:
                print(f"Erro de conexão ao acessar: {url}")
            except requests.exceptions.HTTPError as e:
                print(f"Erro HTTP ({e.response.status_code}) ao baixar: {url}")
                break  
            except requests.exceptions.RequestException as e:
                print(f"Erro inesperado ao baixar {url}: {e}")
            
            tentativas += 1
            if not sucesso and tentativas < max_tentativas:
                print(f"🔁 Tentando novamente em {intervalo} segundos... ({tentativas}/{max_tentativas})")
                time.sleep(intervalo)

        if not sucesso:
            print(f"Falha ao baixar após {max_tentativas} tentativas: {url}")

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    url = "https://laurodefreitas.ba.gov.br"
    close_poupup = "#aviso > div > div > div.modal-header > button"
    button_selector = 'body > header > div > div > div.header-top.black-bg.d-none.d-md-block > div > div > div > div.btn-group > a:nth-child(2) > button'
    table_selector = "#edicoesAnteriores > div.table-responsive > table > tbody"
    edition_column_selector = "#edicoesAnteriores > div.table-responsive > table > tbody > tr > td:nth-child(2)"
    edicoes = []
    page.on("popup", lambda popup: edicoes.extend(handle_popup(popup, table_selector, edition_column_selector)))
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.click(close_poupup)
    page.click(button_selector)
    page.wait_for_timeout(30000)
    browser.close()
    return edicoes

def handle_popup(popup, table_selector, edition_column_selector):
    data = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    if datetime.today().strftime("%A") == "Monday":
        data = (datetime.now() - timedelta(days=3)).strftime("%d/%m/%Y")
    # data = '06/05/2025'

    edicoes = []
    try:
        popup.wait_for_selector(table_selector)
        for i in range(1, 10):
            data_linha = popup.query_selector_all(
                f"#edicoesAnteriores > div.table-responsive > table > tbody > tr:nth-child({i}) > td:nth-child(1)"
            )[0].text_content().strip()
            if data_linha == data:
                texto = popup.query_selector_all(
                    f"#edicoesAnteriores > div.table-responsive > table > tbody > tr:nth-child({i}) > td:nth-child(2)"
                )[0].text_content().strip()
                edicoes.append(texto)
    except Exception as e:
        print(f"Erro ao capturar edições: {e}")
    return edicoes

def enviar_email(conteudo):
    data = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    if datetime.today().strftime("%A") == "Monday":
        data = (datetime.now() - timedelta(days=3)).strftime("%d/%m/%Y")
    # data = '06/05/2025'

    assunto = f"Nomeações e Exonerações - Diário Oficial {data}"
    msg = MIMEMultipart()
    msg["From"] = os.getenv("From")
    msg["To"] = os.getenv("To")
    msg["Subject"] = assunto

    corpo = "\n\n---\n\n".join(conteudo) if conteudo else "Nenhuma nomeação ou exoneração encontrada."
    msg.attach(MIMEText(corpo, "plain"))

    try:
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login("bot.diario.lf@gmail.com", os.getenv("EMAIL_SENHA"))
        servidor.sendmail(msg["From"], msg["To"], msg.as_string())
        servidor.quit()
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

def salvar_exoneracoes_em_excel(resultados, nome_arquivo_excel="exoneracoes.xlsx"):
    """
    Processa os resultados, extrai dados de exoneração, salva os nomes em MAIÚSCULAS
    e os adiciona a um arquivo Excel existente. Se o arquivo não existir, ele é criado.
    """
    padrao = re.compile(r"Nome:\s*(.*?)\s*-\s*Secretaria:\s*(.*?)\s*-\s*Ato:\s*EXONERAÇÃO", re.IGNORECASE)
    novos_dados = []

    print("Iniciando a extração de novas exonerações...")

    for bloco_texto in resultados:
        linhas = bloco_texto.strip().split('\n')
        if not linhas: continue
        
        nome_arquivo = linhas[0].strip()
        if not nome_arquivo.lower().endswith(".pdf"): continue

        try:
            data_str = nome_arquivo[:10]
            data_formatada = datetime.strptime(data_str, '%Y_%m_%d').strftime('%d/%m/%Y')
            edicao = nome_arquivo[10:14]
        except (ValueError, IndexError):
            print(f"  -> Aviso: Não foi possível extrair data/edição do arquivo '{nome_arquivo}'.")
            continue

        for linha in linhas[1:]:
            match = padrao.search(linha.strip())
            if match:
                nome = match.group(1).strip()
                secretaria = match.group(2).strip()
                
                # Adiciona o dicionário com o nome em maiúsculas
                novos_dados.append({
                    "data": data_formatada,
                    "edicao": edicao,
                    "Nome": nome.upper(),  # <-- MUDANÇA AQUI
                    "Secretaria": secretaria
                })

    if not novos_dados:
        print("Nenhuma nova exoneração encontrada para adicionar.")
        return

    df_novos = pd.DataFrame(novos_dados)
    ordem_colunas = ["data", "edicao", "Nome", "Secretaria"]
    df_novos = df_novos[ordem_colunas]
    
    try:
        df_antigo = pd.read_excel(nome_arquivo_excel)
        print(f"Arquivo '{nome_arquivo_excel}' encontrado. Adicionando {len(df_novos)} novos registros.")
        df_final = pd.concat([df_antigo, df_novos], ignore_index=True)
    except FileNotFoundError:
        print(f"Arquivo '{nome_arquivo_excel}' não encontrado. Criando um novo com {len(df_novos)} registros.")
        df_final = df_novos
    except Exception as e:
        print(f"Ocorreu um erro ao ler o arquivo existente: {e}")
        return

    try:
        # Garante que não haja duplicatas baseadas no nome e data
        df_final.drop_duplicates(subset=['Nome', 'data'], keep='last', inplace=True)
        df_final.to_excel(nome_arquivo_excel, index=False)
        print(f"Dados salvos com sucesso em '{os.path.abspath(nome_arquivo_excel)}'. Total de {len(df_final)} registros.")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo Excel: {e}")

def processar_tornar_sem_efeito(resultados, nome_arquivo_excel="historico_exoneracoes.xlsx"):
    """
    Verifica atos "TORNAR SEM EFEITO", convertendo os nomes para MAIÚSCULAS para
    procurar e remover as linhas correspondentes no arquivo Excel.
    """
    print("\n--- Iniciando verificação de atos 'TORNAR SEM EFEITO' ---")
    
    padrao_remocao = re.compile(r"Nome:\s*(.*?)\s*-\s*Secretaria:.*-\s*Ato:\s*TORNAR SEM EFEITO", re.IGNORECASE)
    nomes_para_remover = []
    
    for bloco_texto in resultados:
        for linha in bloco_texto.strip().split('\n'):
            match = padrao_remocao.search(linha)
            if match:
                nome = match.group(1).strip().upper()  # <-- MUDANÇA AQUI
                nomes_para_remover.append(nome)
                print(f"Encontrado ato 'TORNAR SEM EFEITO' para: {nome}")

    if not nomes_para_remover:
        print("Nenhum ato 'TORNAR SEM EFEITO' encontrado nos resultados de hoje. Nenhuma remoção necessária.")
        return

    try:
        df = pd.read_excel(nome_arquivo_excel)
        if 'Nome' not in df.columns:
            print(f"Erro: A coluna 'Nome' não foi encontrada no arquivo '{nome_arquivo_excel}'.")
            return
    except FileNotFoundError:
        print(f"Aviso: O arquivo '{nome_arquivo_excel}' não foi encontrado. Não há nada para remover.")
        return
    except Exception as e:
        print(f"Ocorreu um erro ao ler o arquivo Excel: {e}")
        return

    nomes_na_planilha = df['Nome'].tolist()
    linhas_antes = len(df)

    # A comparação agora é entre a lista de nomes em maiúsculas e a coluna 'Nome' que já está em maiúsculas
    df_filtrado = df[~df['Nome'].isin(nomes_para_remover)]
    
    linhas_depois = len(df_filtrado)

    if linhas_antes > linhas_depois:
        nomes_removidos_confirmados = [nome for nome in nomes_para_remover if nome in nomes_na_planilha]
        
        print("\n--- Relatório de Remoções ---")
        for nome in nomes_removidos_confirmados:
            print(f"REMOVIDO: O registro de '{nome}' foi removido da planilha.")
        
        try:
            df_filtrado.to_excel(nome_arquivo_excel, index=False)
            print(f"\nPlanilha '{nome_arquivo_excel}' atualizada com sucesso. {linhas_antes - linhas_depois} registro(s) removido(s).")
        except Exception as e:
            print(f"Ocorreu um erro ao salvar a planilha atualizada: {e}")
    else:
        print("\nApesar dos atos 'TORNAR SEM EFEITO' encontrados, nenhum nome correspondia a um registro na planilha atual.")

    print("--- Verificação de remoções concluída ---")


@app.task
def run_full_process():
    with sync_playwright() as playwright:
        edicoes = run(playwright)
        print(f"Edições encontradas: {edicoes}")
        download_pdf_requests(edicoes, PASTA_PDFS)
        resultados = processar_diarios_com_llm()
        if resultados:
            salvar_exoneracoes_em_excel(resultados, "relatorio_exoneracoes.xlsx")
            processar_tornar_sem_efeito(resultados, "relatorio_exoneracoes.xlsx")
        enviar_email(resultados)
        mover_arquivos_pasta(PASTA_PDFS, PASTA_DESTINO)
