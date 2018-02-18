from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals
import os
import time
import re
import asyncio
import nltk
from slackclient import SlackClient
# For summarizing articles
from sumy.parsers.html import HtmlParser
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

# For Summarizing articles
nltk.download('punkt')

# For Summarizing
LANGUAGE = "english"
SENTENCES_COUNT = 10

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# Slack id of the bot. It's instantiated on connection
bot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "/"
MENTION_REGEX = "^(bot\s)(.*)"
COMMANDS = ["help - List commands", "summary - Summarize an article. Usage: \"bot /summary ARTICLE_LINK\""]

def parse_bot_commands(slack_events):
  """
    Parses text from Slack and handles event if it's a Bot command
    If commands return the command, channel
    If not command return None, None
  """
  for event in slack_events:
    if event["type"] == "message" and not "subtype" in event:
      # Parse event to see if it mentions bot directly
      user_id, message = parse_direct_mention(event["text"])
      if user_id is not None and user_id.strip() == "bot":
        # If event mentions bot return to main function with params
        return message, event["channel"]
  return None, None

def parse_direct_mention(msg_text):
  """
      Finds a direct mention (a mention that is at the beginning) in message text
      and returns the user ID which was mentioned. If there is no direct mention, returns None
  """
  matches = re.search(MENTION_REGEX, msg_text)
  # First group contains username, next contains message
  return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

# Summarize articles
def get_summary(article):
  url = article
  parser = HtmlParser.from_url(url, Tokenizer(LANGUAGE))
  # or for plain text files
  # parser = PlaintextParser.from_file("document.txt", Tokenizer(LANGUAGE))
  stemmer = Stemmer(LANGUAGE)

  summarizer = Summarizer(stemmer)
  summarizer.stop_words = get_stop_words(LANGUAGE)

  parsed_articled = ""

  for sentence in summarizer(parser.document, SENTENCES_COUNT):
      parsed_articled += (str(sentence) + "\n")

  return parsed_articled

def handle_command(command, channel):
  """
    Execute command
  """
  default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)

  # Var to store bot response
  response = None

  # Check if command starts with "do"
  if command.startswith(EXAMPLE_COMMAND):
    # Empty args for n+1 loops
    args = ""
    # Split command to get args
    args = command.lower().split(' ')
    # Get which command is called
    command = args[0][1:]
    print("command: " + command)
    # Remove <> from URL argument if args[1] exists
    # For some reason there isn't a check in Python for if index exists?
    try:
      if args[1]:
        argument = re.sub('([<>])', '', args[1])
        print("argument: " + argument)
    except AttributeError:
      pass
    except IndexError:
      pass

    if command == "help":
      str = ""
      for x in COMMANDS:
        str += "/" + x + "\n"

      response = "Available commands:\n" + str
    elif command == "summary" and argument:
      response = get_summary(argument)
    elif command not in COMMANDS:
      response = "Sure ... Write some more code and I will do that"

  # Sends the response back to the channel
  slack_client.api_call(
      "chat.postMessage",
      channel=channel,
      text=response or default_response
  )

if __name__ == "__main__": 
  if slack_client.rtm_connect(with_team_state=False):
    print("Fypster Slack Bot connected and running!")
    # Get bot id from Slack
    bot_id = slack_client.api_call("auth.test")["user_id"]
    # Enter infinite loop for processing messages
    while True:
      # Read commands from Slack and save into vars
      command, channel = parse_bot_commands(slack_client.rtm_read())
      if command:
        handle_command(command, channel)
      time.sleep(RTM_READ_DELAY)
  else:
    print("Error connecting to Slack")