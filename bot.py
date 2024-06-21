#Get question from user when they start the question with "!ask"

#Send question to AI Agent

#Get reply from AI Agent

#Create thread on question and put the reply there


import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)


class DiscordBot():

    def __init__(self, humansupport_name, bothelp_name, guild_name, questions_list):
        # Load environment variables from .env file
        load_dotenv('.env')
        
        # Define the bot with necessary intents
        intents = discord.Intents.default()
        intents.message_content = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)

        # Get the bot token from the environment variable
        self.TOKEN = os.getenv('DISCORD_TOKEN')

        self.setup_bot_commands()

        self.humansupport_name = humansupport_name
        self.bothelp_name = bothelp_name
        self.guild_name = guild_name
        self.question_lists = questions_list
        self.bot_task = None
        self.loop = asyncio.get_event_loop()
        self.runtime_exception = None

    def setup_bot_commands(self):
        # Event handler for when the bot is ready
        @self.bot.event
        async def on_ready():
            logging.info(f'Logged in as {self.bot.user.name}')

        @self.bot.event
        async def on_error(event_method, *args, **kwargs):
            logging.error(f"An error occurred in {event_method}: with args: {args if args else 'None'} and kwargs: {kwargs if kwargs else 'None'}")
            exception = sys.exception()
            logging.error(f"Exception: {exception}")
            self.runtime_exception = exception
            await self.cleanup()  # Clean up resources

        # General message listener to check if the bot receives any messages
        @self.bot.event
        async def on_message(message):
            logging.info(f'Message from {message.author}: {message.content}')
            await self.bot.process_commands(message)

        # Command to get a question from the user
        @self.bot.command(name='ask')
        async def ask_question(ctx, *, question: str):
            bothelp_channel = self.get_channel(self.bothelp_name)
            if ctx.channel != bothelp_channel:
                logging.info("Wrong channel for ask")
                return
            logging.info(f'Question from {ctx.author}: {question}')
            #await self.send_response("Hello world", ctx.message)
            self.question_lists.append(ctx.message)

    async def send_response(self, response, message):
        #channel_id = YOUR_CHANNEL_ID  # Replace with your channel ID
        #channel = self.bot.get_channel(channel)
        response_thread = await message.create_thread(name=message.content)
        await response_thread.send(response)

    def get_channel(self, channel_name):
        guilds = self.bot.guilds
        for guild in guilds:
            if guild.name == self.guild_name:
                for channel in guild.text_channels:
                    if channel_name == channel.name:
                        return channel
    
    async def human_support(self, question):
        human_support_channel = self.get_channel(self.humansupport_name)
        support_message = await human_support_channel.send(question.content)
        await support_message.add_reaction("⭐")

    #split up process to run in parallel
    async def start(self):
        """
        Start the bot, ensuring it returns quickly as required by the framework.
        :param token: The token used to log in to Discord.
        """
        # Start the bot asynchronously and ensure it returns immediately.
        if not self.bot_task:
            try:
                self.bot_task = self.loop.create_task(self.start_bot_async())
            except Exception as e:
                # Log the exception or handle it appropriately
                logging.error(f"Error starting the bot: {e}")
                raise e  # Re-raise to notify the outer scope (if necessary)
        return "Bot startup initiated"
    

    async def start_bot_async(self):
        """Starts the bot as an asyncio task."""
        logging.info("Starting bot...")
        try:
            await self.bot.start(self.TOKEN)
            logging.info("Bot started successfully.")
        except Exception as e:
            logging.error(f"Exception in bot start: {e}")
            raise e

    async def cleanup(self):
        """Cleans up resources, including closing network sessions and other cleanable resources."""
        logging.info("Cleaning up resources...")
        if not self.bot.is_closed():
            await self.bot.close()  # Close the bot connection properly
        tasks = [t for t in asyncio.all_tasks()]
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass 

async def main():
    questions_list = []
    bot = DiscordBot("escalate-to-human", "ask-bot-help", "AV AIChatbot Server", questions_list)
    await bot.start()
    await asyncio.sleep(10)
    logging.info("Running")
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logging.error("Task has been cancelled")
    except Exception as e:
        logging.error(f"Exception caught : {e}")
    finally:
        pass
