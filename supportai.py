
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
    
    def __init__(self, context_num, model_name, temp_num, test_mode):
        
        load_dotenv('.env')
        
        self.questions_list = []
        self.humansupport_name = "escalate-to-human"
        self.bothelp_name = "help-channel"
        self.guild_name = "AV AIChatbot Server"
        self.discordbot = DiscordBot(self.humansupport_name, self.bothelp_name, self.guild_name, self.questions_list)
        self.vectorize_key = os.getenv('VECTORIZE_KEY')
        self.context_num = context_num
        self.model_name = model_name
        self.temp_num = temp_num
        self.groq_key = os.getenv('GROQ_API_KEY')
        self.test_token=os.getenv('TEST_TOKEN')
        self.test_url=os.getenv('TEST_URL')
        self.test_mode= test_mode
        self.vectorize_url=os.getenv('VECTORIZE_URL')

    async def start_bot(self):
        await self.discordbot.start()

    async def question_to_be_processed(self):
        while(True):
            if len(self.questions_list) > 0:
                questioninformation = self.questions_list.pop(0)
                question=questioninformation[0]
                #print(questioninformation, question)
                await self.process_question(question, questionthread=questioninformation[1])
            else:
                await asyncio.sleep(1)
    
    #switch to retrieve_context after vectorize works
    async def process_question(self, question, questionthread):
        try:
            context = await self.retrieve_context(question)
            answer = await self.send_to_LLM(context, question)
            answer+="\n **If I answered your question correctly, please add a thumbs up to this message. If you were not satisfied, add a thumbs down.**"
            if "apologize" in answer:
                await self.discordbot.send_response(answer, questionthread)
                await self.discordbot.human_support(questionthread)
            else:
                await self.discordbot.send_response(answer, questionthread)
        except Exception as e:
            logging.error(f"Error processing question: {e}")
            #await self.discordbot.send_response("An error occurred while processing your question. Please try again later.", question)
            raise e

    async def retrieve_context(self,question):
        if self.test_mode == True:
            url = f'{self.test_url}'
            headers = {
                'Content-Type': 'application/json' ,
                'authorization' : f'{self.test_token}'
            }
        else:
            url = f'{self.vectorize_url}'
            headers = {
                'Content-Type': 'application/json',
                'authorization' : f'{self.vectorize_key}'
            }
        question = question.replace("!ask", "")
        #changed from self.vectorizekey to self.test_cred
        
        data = {
            "question": question,
            "numResults": self.context_num
        }

        #CHANGE to test_URL
        response = requests.post(url, headers=headers, json=data)
        print("Vectorize API returned")
        if response.status_code == 200:
            response_dict = response.json()
            response_value=None
            if 'record' in response_dict and 'value' in response_dict['record']:
                response_value = response_dict["record"]["value"]
            #logging.info(response_value)
            response_value=json.loads(response_value)
            related_docs=response_value["related_documents"]
            #related_docs=json.loads(related_docs)
            result=""
            #logging.info(related_docs[0]["origin"])
            #logging.info(related_docs[0]["source"])
            for doc in related_docs:
                result+="-----" + "Start of document: "
                if doc["origin"]=="discord":
                    result+="source of document: "+await self.builddiscordsourcelink(doc["source"]) + "   ---   "
                else:
                    result+="source of document: "+doc["source"] + "   ---   "
    
                result+= "text of document: "+ doc["text"] + "  End of document "
            #logging.info(result)
           # logging.info(f"Doc: {doc}")
            return result
            logging.info(f"Response from Vectorize API: {response_dict}")
            # if 'value' in response_dict and 'text' in response_dict['value']:
            #     context = response_dict["value"]["text"]
            #     logging.info(context)
            #     return context
            # else:
            #     raise Exception(f"Unexpected response structure: {response_dict}")
        else:
            raise Exception(f"Error in retrieving context: {response.text}")
        
    async def builddiscordsourcelink(self, sourcestr):
        print("Printing source string: "+sourcestr)
        baseurl="https://discord.com/channels/"
        baseurl+=str(self.discordbot.returnguildid()) +"/"
        #print(baseurl)
        source=sourcestr.split("/")
        channelid=await self.discordbot.returnchannelid(source[0])
        baseurl+=str(channelid)+"/threads/"
        #print(baseurl)
        baseurl+=str(await self.discordbot.returnthreadid(channelid, source[1]))+"/"
        #print(baseurl)
        return baseurl


        
    async def send_to_LLM(self, context, question):
        #Send context and question to LLM
        systemText= f"""You are an expert programmer and problem-solver, tasked to answer any question about Groq.
            Using the provided context, answer the user's question to the best of your ability using the resources provided.
            Generate a comprehensive and informative answer for a given question.
            You must only use information from the provided and relevant documents.
            Use an unbiased and journalistic tone.
            Combine search results together into a coherent answer.
            Do not repeat text.
            Cite search results using [${{number}}] notation.
            Only cite the most relevant results that answer the question accurately.
            Place these citations at the end of the sentence or paragraph that reference them - do not put them all at the end.
            Along with the citation, please include the source of the relevant document as provided in part of the document.
            If different results refer to different entities within the same name, write separate answers for each entity.
            If there is nothing in the context relevant to the question at hand, just say "I apologize, but I do not have the answer for that question at this time" Don't try to make up an answer.

            You should use bullet points in your answer for readability
            Put citations where they apply rather than putting them all at the end.

            REMEMBER: If there is no relevant information within the context, just say "I apologize, but I do not have the answer for that question at this time." Don't try to make up an answer.
            Anything between the preceding 'context' html blocks is retrieved from a knowledge bank, not part of the conversation with the user. """

        systemText1 = "You are a technical customer support agent. Please provide a response to the customer's questions."
        system_prompt = {
            "role": "system",
            "content": systemText
        }

        #currently using context.txt for an example as to what the vectorize API call would return
        promptText = f"""
        {context}
        The above documents are provided to assist you in answering the following question. 
        Use only the provided documents to generate a response, if the documents do not provide sufficient information to answer the question below respond saying exactly that there is not enough information. If the answer can not be found in the provided documents, say "I apologize, but I do not have the answer for that question at this time"
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
            print("Groq API returned")
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
        #logging.info(f"Response from LLM: {response}")

        if 'error' not in response:
            answer = response.choices[0].message.content
            return answer
        else:
            raise Exception(f"Error in sending to LLM: {response.error}")



async def main():
    agent = ai_agent(2, "llama3-70b-8192", 0.5, True)
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


