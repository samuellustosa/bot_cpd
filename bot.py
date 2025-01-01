import os
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# Configuração inicial
TOKEN = "7203695932:AAHHq_YdDYpARzoxSAiBAQQd6gF-TQfU8wM"
DIRETORIO_IMAGENS = "imagens"
ARQUIVO_SOLUCOES = "solucoes.json"
os.makedirs(DIRETORIO_IMAGENS, exist_ok=True)

# Funções para persistência de dados
def carregar_solucoes():
    try:
        with open(ARQUIVO_SOLUCOES, "r") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        return {}

def salvar_solucoes(solucoes):
    with open(ARQUIVO_SOLUCOES, "w") as arquivo:
        json.dump(solucoes, arquivo, indent=4)

solucoes = carregar_solucoes()

# Funções principais do bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe opções iniciais para o usuário."""
    keyboard = [
        [InlineKeyboardButton("Adicionar Solução", callback_data="adicionar_solucao")],
        [InlineKeyboardButton("Buscar Soluções", callback_data="buscar_solucoes")],
        [InlineKeyboardButton("Excluir Solução", callback_data="excluir_solucao")],
        [InlineKeyboardButton("Ajuda", callback_data="ajuda")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Olá! Sou o Bot do CPD. Escolha uma opção:", reply_markup=reply_markup)

# Função para gerenciar os botões
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia interações dos botões."""
    query = update.callback_query
    await query.answer()

    # Define o teclado de resposta
    keyboard = [
        [InlineKeyboardButton("Adicionar Solução", callback_data="adicionar_solucao")],
        [InlineKeyboardButton("Buscar Soluções", callback_data="buscar_solucoes")],
        [InlineKeyboardButton("Excluir Solução", callback_data="excluir_solucao")],
        [InlineKeyboardButton("Ajuda", callback_data="ajuda")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.data == "adicionar_solucao":
        novo_texto = "Envie o texto ou imagem da solução para adicioná-la."
        await query.message.reply_text(novo_texto, reply_markup=reply_markup)
        context.user_data["modo"] = "adicionar_solucao"

    elif query.data == "listar_solucoes":
        await listar_solucoes(update, context, pagina=1)

    elif query.data == "buscar_solucoes":
        novo_texto = "Envie o termo que deseja buscar."
        await query.message.reply_text(novo_texto, reply_markup=reply_markup)
        context.user_data["modo"] = "buscar_solucoes"

    elif query.data == "excluir_solucao":
        novo_texto = "Envie o ID da solução que deseja excluir."
        await query.message.reply_text(novo_texto, reply_markup=reply_markup)
        context.user_data["modo"] = "excluir_solucao"

    elif query.data == "ajuda":
        await ajuda(update, context)  # Aqui chamamos a função de ajuda corretamente

# Função de ajuda
async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe uma mensagem de ajuda com as opções do bot."""
    texto_ajuda = """
    Olá! Sou o Bot do CPD. Aqui estão os comandos disponíveis:

    📌 **/start**: Comece a interação com o bot.

    📝 **Adicionar Solução**: Envie um texto ou imagem para adicionar uma nova solução.

    🔍 **Buscar Soluções**: Pesquise soluções com base em um termo específico.

    ❌ **Excluir Solução**: Exclua uma solução pelo ID.

    Estou à disposição para ajudar!
    
    by: samuel
    """

    # Verifica se a interação foi com uma mensagem ou callback_query
    if update.callback_query:
        await update.callback_query.answer()  # Responde ao callback
        await update.callback_query.message.reply_text(texto_ajuda)  # Envia a ajuda
    elif update.message:
        await update.message.reply_text(texto_ajuda)  # Caso a ajuda seja acionada via texto

# Função de salvar imagem
async def salvar_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva imagens enviadas pelo usuário.""" 
    modo = context.user_data.get("modo")

    if modo == "adicionar_solucao" and update.message.photo:
        foto = update.message.photo[-1]
        descricao = update.message.caption or "Sem descrição"
        id_solucao = str(len(solucoes) + 1)

        caminho_imagem = os.path.join(DIRETORIO_IMAGENS, f"solucao_{id_solucao}.jpg")
        file = await foto.get_file()
        await file.download_to_drive(caminho_imagem)

        solucoes[id_solucao] = {"texto": descricao, "imagem": caminho_imagem}
        salvar_solucoes(solucoes)
        await update.message.reply_text(f"✅ Solução com imagem adicionada com ID: {id_solucao}")
        context.user_data["modo"] = None

# Função para gerenciar texto
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia entrada de texto do usuário.""" 
    modo = context.user_data.get("modo", None)
    texto = update.message.text

    if modo == "adicionar_solucao":
        id_solucao = str(len(solucoes) + 1)
        solucoes[id_solucao] = {"texto": texto, "imagem": None}
        salvar_solucoes(solucoes)
        await update.message.reply_text(f"✅ Solução adicionada com ID: {id_solucao}\nDescrição: {texto}")
        context.user_data["modo"] = None

    elif modo == "buscar_solucoes":
        if not texto.strip():
            await update.message.reply_text("Você precisa fornecer um termo de busca.")
            return
        resultados = [
            (id, dados)
            for id, dados in solucoes.items()
            if texto.lower() in dados['texto'].lower()
        ]
        if resultados:
            for id_solucao, dados in resultados:
                texto = dados.get("texto", "Sem descrição")
                imagem = dados.get("imagem")

                if imagem:
                    with open(imagem, "rb") as file:
                        await update.message.reply_photo(photo=file, caption=f"ID: {id_solucao}\n{texto}")
                else:
                    await update.message.reply_text(f"ID: {id_solucao}\n{texto}")
        else:
            await update.message.reply_text("Nenhuma solução encontrada.")

    elif modo == "excluir_solucao":
        if texto in solucoes:
            del solucoes[texto]
            salvar_solucoes(solucoes)
            await update.message.reply_text(f"❌ Solução com ID {texto} foi excluída.")
        else:
            await update.message.reply_text("ID inválido. Tente novamente.")
        context.user_data["modo"] = None

# Inicializando o Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot está funcionando!"

# Função para rodar o bot em uma thread separada
def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
    application.add_handler(MessageHandler(filters.PHOTO, salvar_imagem))
    application.run_polling()

# Rodando o servidor Flask e o bot em threads separadas
if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host='0.0.0.0', port=5000)
