from flask import Flask, request, jsonify
import fitz  # PyMuPDF para extrair texto de PDF
import re
import openai
import os

app = Flask(__name__)

# Configuração do token de autenticação e chave da OpenAI
auth_token = os.getenv("AUTH_TOKEN", "meu_novo_token_secreto")  # Utilize variável de ambiente para segurança
openai.api_key = os.getenv("OPENAI_API_KEY", "sua_chave_openai")

# Função para verificar token de autenticação
def verificar_token():
    token = request.headers.get("Authorization")
    if token != f"Bearer {auth_token}":
        return jsonify({"erro": "Não autorizado"}), 403
    return None

# Função para extrair texto do PDF
def extrair_texto_pdf(arquivo_pdf):
    try:
        texto = ""
        with fitz.open(arquivo_pdf) as pdf:
            for pagina in pdf:
                texto += pagina.get_text()
        return texto
    except Exception as e:
        return f"Erro ao extrair texto do PDF: {str(e)}"

# Função para dividir o documento em temas específicos
def dividir_documento_em_temas(texto):
    temas = {
        "Identificação das Partes": re.search(r"(partes|envolvidos|réu|acusado|vítima):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
        "Fatos": re.search(r"(fatos|ocorrências):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
        "Elementos de Prova": re.search(r"(prova[s]?|evidências):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
        "Argumentos da Acusação": re.search(r"(acusação|fundamento do mp):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
        "Argumentos da Defesa": re.search(r"(defesa|alegações):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
        "Jurisprudência e Doutrina": re.search(r"(jurisprudência|doutrina aplicada):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
        "Decisões Interlocutórias": re.search(r"(decisão interlocutória|liminar|medida cautelar):\s*(.*?)\n\n", texto, re.IGNORECASE | re.DOTALL),
    }
    return temas

# Função principal para fazer a análise completa e enviar ao GPT-3.5 Turbo
def analise_juridica_completa(texto):
    temas = dividir_documento_em_temas(texto)
    resultado_analise = {}

    # Dividir o texto em temas principais e adicionar ao resultado de análise
    for tema, conteudo in temas.items():
        resultado_analise[tema] = conteudo.group(2) if conteudo else "Informação não disponível"

    # Análise de cada parte através do modelo GPT-3.5 Turbo
    analises_gpt = {}
    for tema, conteudo in resultado_analise.items():
        if conteudo != "Informação não disponível":
            prompt = (
                f"Realize uma análise jurídica detalhada sobre o tema '{tema}'. "
                "Considere os seguintes aspectos:\n"
                "- Pontos fortes da acusação e da defesa\n"
                "- Fatos importantes a serem destacados\n"
                "- Artigos do Código Penal relacionados ao tema\n"
                "- Recomendações estratégicas para a acusação\n"
                "- Recomendações estratégicas para a defesa\n"
                f"Conteúdo para análise:\n{conteudo}"
            )

            try:
                resposta_gpt = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Você é um assistente jurídico experiente, especializado em análise de processos criminais."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500
                )
                analises_gpt[tema] = resposta_gpt.choices[0].message['content'].strip()
            except Exception as e:
                analises_gpt[tema] = f"Erro ao gerar análise com GPT-3.5: {str(e)}"

    # Adicionando as análises detalhadas ao resultado final
    resultado_analise["Análises Detalhadas"] = analises_gpt

    # Recomendações Estratégicas Finais
    resultado_analise["Recomendações Estratégicas para Acusação"] = (
        "Reforçar a credibilidade das provas e utilizar doutrina aplicável para garantir o convencimento do juiz."
    )
    resultado_analise["Recomendações Estratégicas para Defesa"] = (
        "Impugnar provas duvidosas e enfatizar excludentes de ilicitude ou falta de provas concretas."
    )

    return resultado_analise

@app.route('/upload_arquivo', methods=['POST'])
def upload_arquivo():
    # Verifica o token de autenticação
    auth = verificar_token()
    if auth is not None:
        return auth

    # Verifica se o arquivo PDF foi enviado
    if 'arquivo' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado."}), 400

    arquivo = request.files['arquivo']
    texto = extrair_texto_pdf(arquivo)

    # Tratamento de erro ao extrair texto
    if "Erro ao extrair texto do PDF" in texto:
        return jsonify({"erro": texto}), 400

    # Realiza análise jurídica completa no conteúdo do documento
    resultado_analise = analise_juridica_completa(texto)
    return jsonify(resultado_analise)

    # Atualização para rodar na porta 8080
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)  # Use a porta desejada (8080, por exemplo)
