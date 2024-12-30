from flask import Flask, request, jsonify
import os
import google.generativeai as genai
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import START, MessagesState, StateGraph
from dotenv import load_dotenv
import json 
import requests

#Carregando o .env
load_dotenv()
#Inicializando a LLM
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_API_KEY_SEARCH_CUSTOM = os.getenv('GOOGLE_API_KEY_SEARCH_CUSTOM')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')
HUGGING_FACE_TOKEN = os.getenv('HUGGING_FACE_TOKEN')
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

#Configurando Memória da LLM
workflow = StateGraph(state_schema=MessagesState)

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}

workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

#Agente de Busca

def search_function(topic):
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        'q': topic,
        'key': GOOGLE_API_KEY_SEARCH_CUSTOM,
        'cx': SEARCH_ENGINE_ID,
        'searchType': 'text'
    }
    response = requests.get(url, params=params)
    search_results = response.json()

    results = []
    for result in search_results['items']:
        results.append(result['title'] + ": " + result['snippet'])
    print("Entrei aqui")
    return results

search = Tool(
    name="search",
    func=search_function,
    description="Busca por um tópico na web."
)

tools = [search]

#Personalidade do agente
personality = "Você é um agente de IA que tem como objetivo engajar em conversas interessantes e informativas sobre uma ampla gama de tópicos com o usuário. Você pode falar sobre qualquer assunto, como tecnologia, arte, ciência, história, cultura, esportes, entretenimento, e muito mais. No entanto, você deve evitar qualquer discussão relacionada à Engenharia Civil. Quando o usuário tentar abordar tópicos relacionados à Engenharia Civil, gentilmente redirecione a conversa para um assunto diferente, sem entrar em detalhes sobre esse tema específico. Mantenha a conversa fluída, amigável e interessante."

prompt_template_chatbot = ChatPromptTemplate.from_messages([
    ("system", personality),
    MessagesPlaceholder(variable_name="history"),
    ("human", "Dúvida do usuário : {input}")
])

app = Flask(__name__)

def needs_search(user_input): 
    keywords = ["quem", "quando", "onde", "como", "o que", "qual"]
    return any(keyword in user_input.lower() for keyword in keywords)

conversation_history = {}
conversation_id = 0

def save_conversation(user_input, response_text):
    global conversation_id
    conversation_history[conversation_id] = {
        "user": user_input,
        "assistant": response_text
    }
    conversation_id += 1
    with open('conversation_history.json', 'w') as f:
        json.dump(conversation_history, f, indent=2)

def generate_response(user_input):
    if needs_search(user_input):
        search_results = search_function(user_input)
        prompt = f"Você é um assistente útil. Você tem essa personalidade: {personality}. Responda a essa pergunta: {user_input}. Com base nos resultados da pesquisa: {search_results}"
    else: 
        prompt = f"Você é um assistente útil. Você tem essa personalidade: {personality}. Responda a essa pergunta: {user_input}."
    response = model.generate_content(prompt)
    return response.text

@app.route('/conversar', methods=['POST'])
def conversar():
    user_input = request.json['pergunta']
    response = generate_response(user_input)
    save_conversation(user_input, response)
    return jsonify({'resposta': response})

if __name__ == '__main__':
    app.run(debug=True)