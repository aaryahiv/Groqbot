
#Get question  from discord server

#Send question to vectorize retrieval endpoint

#Send context and question to LLM

#Based on reply from LLM, elevate to human or send reply to discord bot

from bot import DiscordBot
import asyncio
import logging
import sys
import requests
import os
from dotenv import load_dotenv
import json
from groq import Groq

class ai_agent():
    
    def __init__(self, context_num, model_name, temp_num):
        
        load_dotenv('.env')
        
        self.questions_list = []
        self.humansupport_name = "escalate-to-human"
        self.bothelp_name = "ask-bot-help"
        self.guild_name = "AV AIChatbot Server"
        self.discordbot = DiscordBot(self.humansupport_name, self.bothelp_name, self.guild_name, self.questions_list)
        self.vectorize_key = os.getenv('VECTORIZE_KEY')
        self.context_num = context_num
        self.model_name = model_name
        self.temp_num = temp_num
        self.groq_key = os.getenv('GROQ_API_KEY')

    async def start_bot(self):
        await self.discordbot.start()

    async def question_to_be_processed(self):
        while(True):
            if len(self.questions_list) > 0:
                question = self.questions_list.pop(0)
                await self.process_question(question)
            else:
                await asyncio.sleep(5)
    
    #switch to retrieve_context after vectorize works
    async def process_question(self, question):
        #context = await self.retrieve_context(question)
        with open('context.txt', 'r') as file:
            context = file.read()        
        answer = await self.send_to_LLM(context, question.content)
        if "apologize" in answer:
            await self.discordbot.human_support(question)
        else:
            await self.discordbot.send_response(answer,question)

    async def retrieve_context(self, question):
        # Send question to vectorize retrieval endpoint
        url = f'https://client.app.vectorize.io/api/gateways/service/od2c-bccb222dcc4d/retrieve?credentials={self.vectorize_key}'
        headers = {
            'Content-Type': 'text/plain'
        }
        data = {
            "question": question,
            "numResults": self.context_num
        }

        response = requests.post(url, headers=headers, json=data)
        response_dict = response.json()
        context = response_dict["value"]["text"]
        if response.status_code == 200:
            return context # Assuming the response is in JSON format
        else:
            raise Exception(f"Error in retrieving context: {response.text}")

    async def send_to_LLM(self, context, question):
        #Send context and question to LLM
        systemText = "You are a technical customer support agent. Please provide a response to the customer's questions."
        system_prompt = {
            "role": "system",
            "content": systemText
        }
        promptText = f"""
        {context}
        The above documents are provided to assist you in answering the following question. 
        Use only the provided documents to generate a response, if the documents do not provide sufficient information to answer the question below respond saying exactly that there is not enough information:
        {question}
        """   
        prompt = {
            "role": "user",
            "content": promptText
        }     
        model = self.model_name
        temperature = self.temp_num
        top_p = 1.0
        
        try:
            client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )
            response = client.chat.completions.create(
                messages=[system_prompt, prompt],
                model=model,
                temperature=temperature,
                max_tokens=800,
                top_p=top_p,
                frequency_penalty=0,
                presence_penalty=0,
            )

        except Exception as e:
            logging.error(f"Error in sending to LLM: {e}")
            raise e
        
        # url = "https://api.groq.com/openai/v1/chat/completions"
        # headers = {
        #     "Content-Type": "application/json",
        #     "Authorization": f"Bearer {self.groq_key}",
        #     "Cache-Control": "no-cache"
        # }

        # payload = {
        #     "messages": [system_prompt, prompt],
        #     "model": "model",
        #     "temperature": temperature,
        #     "top_p": top_p
        # }

        # response = requests.post(url, headers=headers, data=json.dumps(payload))
        # response_dict = json.loads(response)
        # logging.info(f"System Text: {systemText}")
        # logging.info(f"Prompt Text: {promptText}")
        logging.info(f"Response from LLM: {response}")

        if 'error' not in response:
            answer = response.choices[0].message.content
            return answer
        else:
            raise Exception(f"Error in sending to LLM: {response.error}")



async def main():
    agent = ai_agent(5, "llama3-8b-8192", 0.5)
    await agent.start_bot()
    await asyncio.sleep(3)
    await agent.question_to_be_processed()
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logging.error("Task has been cancelled")
    except Exception as e:
        logging.error(f"Exception caught : {e}")
    finally:
        pass


