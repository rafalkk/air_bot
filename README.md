## Air Bot PL

### Introduction

Air Bot PL is a Telegram bot that provides air quality information based on data from the Polish Chief Inspectorate for Environmental Protection ([GIOS](https://powietrze.gios.gov.pl/pjp/home?lang=en)). It is written in Python and uses the pyTelegramBotAPI library.

### How to use
Start conversation with **@pl_air_bot** on telegram

#### Available commands:

    /start: Displays the bot's introduction and version information.

    /help: Provides a list of available commands and how to use them.

    /types: Lists the types of air pollutants measured along with their respective norms.

    /all: Lists the IDs and names of all available air measurement stations.

    'air id': Retrieves air quality measurements from a specific station by providing its ID (e.g., 'air 10955').

    'loc latitude longitude': Retrieves air quality measurements from the station closest to the given coordinates (e.g. 'loc 54.35 18.6667').

    Share Location: Sends the current location to get air quality measurements from the closest station.

### Run by yourself

#### Obtain a Telegram bot authentication token at https://core.telegram.org/bots

#### Download source code
You will need to have Python3 and pip installed. 
Github releases will allow you to easily select a version.

#### Install required Python libraries:
    pip install -r requirements.txt

#### Set an environment variable named TELEGRAM_BOT_API_KEY with obtained token.
linux bash:

    export TELEGRAM_BOT_API_KEY=your-api-key
windows powershell:

    $env:TELEGRAM_BOT_API_KEY = "your-api-key"


#### Run the script.
    python ./bot.py  

#### Optional proxy use
If you have trouble connecting from your IP, you can use a [scrapeops proxy](https://scrapeops.io/docs/intro/). Set the proxy api key as an environment variable, the application will automatically use the proxy if TELEGRAM_BOT_PROXY_API_KEY env is present.

linux bash:

    export TELEGRAM_BOT_PROXY_API_KEY=your-api-key
windows powershell:

    $env:TELEGRAM_BOT_PROXY_API_KEY = "your-api-key"

### Docker Image
You can download docker image from github packages or build your own using dockerfile form repository.

When you have image, you need to pass TELEGRAM_BOT_API_KEY as environment variable.

    docker run -e TELEGRAM_BOT_API_KEY=your-api-key yourContainerName

proxy api key optionally

    docker run -e TELEGRAM_BOT_API_KEY=your-api-key -e TELEGRAM_BOT_PROXY_API_KEY=your-api-key yourContainerName