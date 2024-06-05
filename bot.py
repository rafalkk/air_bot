import os
import requests
from geopy import distance
import logging
import logging.handlers

# pyTelegramBotAPI
import telebot

# REMEBER TO UPDATE VERSION
version = "1.0.2"
# REMEBER TO UPDATE VERSION

# Global variable to control proxy usage
USE_PROXY = False

# Environmental variables required to run bot
TELEGRAM_API_KEY = os.environ.get("TELEGRAM_BOT_API_KEY")
PROXY_API_KEY = os.environ.get("TELEGRAM_BOT_PROXY_API_KEY")

# Check if the Proxy Api Key environmental variable is set
if 'TELEGRAM_BOT_PROXY_API_KEY' in os.environ:
    USE_PROXY = True
print(f'proxy is used: {USE_PROXY}')

# Create a Telebot instance
bot = telebot.TeleBot(TELEGRAM_API_KEY)

# Create a folder for log files if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging configuration
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('logs/error.log', maxBytes=1048576, backupCount=3),
        logging.StreamHandler()
    ]
)


def craft_proxy_request(original_url, **kwargs):
    """
    Takes the original api url and wraps it with scrapeops.io proxy api parameters.
    If global var USE_PROXY is set to false, make a regular request. Default timeout is set in this function.
    """
    timeout = 10

    if USE_PROXY:
        url = "https://proxy.scrapeops.io/v1/"
        params = {
            "api_key": PROXY_API_KEY,
            "url": original_url,
            "country": "PL",
        }
        return requests.get(url, params=params, timeout=timeout, **kwargs)
    else:
        return requests.get(original_url, timeout=timeout, **kwargs)



def msg_string_format(list):
    """
    Takes list of readings. Format value to two decimal points.
    If the value is equal to "no data", it means that there were no values to read.
    """

    norms = {
    "PM10" : 50,
    "PM2.5" : 20,
    "CO" : 10000,
    "SO2" : 350,
    "NO2" : 200,
    "C6H6" : 5,
    "O3" : 120
}
    
    raw_string = ""
    max_key_length = max(len(dict["key"]) for dict in list)
    max_value_length = max(len(str(round(dict["value"],1))) for dict in list)

    for dict in list:
        key = dict["key"]
        value = dict["value"]

        if value == "no data":
            raw_string += f'{key.ljust(max_key_length)} : {"no data".ljust(max_value_length)}' + "\n"
        else:
            value2f = f'{value:.1f}'
            raw_string += f'{key.ljust(max_key_length)} : {value2f.ljust(max_value_length)} : {(value/norms[key]*100):.0f}%' + "\n"
    
    return raw_string


def long_msg(msg, max_char=4096):
    """
    Takes string and return a list of smaller strings.
    Defult 4096 is max number of chars in one telegram message.
    """
    return [msg[i : i + max_char] for i in range(0, len(msg), max_char)]


def air_command_test(msg):
    """Syntax test for the "AIR" command."""
    command = msg.text.split()
    return len(command) == 2 and command[0].upper() == "AIR"


def loc_command_test(msg):
    """Syntax test for the "LOC" command."""
    command = msg.text.split()
    return len(command) == 3 and command[0].upper() == "LOC"


def gios_distance(user_location):
    """Takes (latitude, longitude) tuple (both floats) and
    return dict of ids and calculated distances to stations.
    """
    # Get all station data
    all = gios_get_all()

    # If gios_get_all() returns an error, return the error.
    if isinstance(all, Exception):
        return all

    distances = {
        station["id"]: distance.great_circle(
            user_location, (station["gegrLat"], station["gegrLon"])
        ).km
        for station in all
    }

    return distances


def gios_get_all():
    """Get a list and info of all air measurement stations."""
    # Contact API
    try:
        url = "https://api.gios.gov.pl/pjp-api/rest/station/findAll"
        
        response = craft_proxy_request(url)
        
        return response.json()
            
    except requests.exceptions.RequestException as err:
        logging.error(f"RequestException occurred: {str(err)}")
        return err
    except Exception as err:
        logging.error(f"An error occurred: {str(err)}")
        return err


def gios_get_sensors(station_id):
    """Get a list of measuring sensors from a given id of measurement station."""
    # Contact API
    try:
        url = f"https://api.gios.gov.pl/pjp-api/rest/station/sensors/{int(station_id)}"
        response = craft_proxy_request(url)
        return response.json()

    except requests.exceptions.RequestException as err:
        logging.error(f"RequestException occurred: {str(err)}")
        return err
    except Exception as err:
        logging.error(f"An error occurred: {str(err)}")
        return err


def gios_get_data(sensor_id):
    """Get measuring data form a given id of sensor id."""
    # Contact API
    try:
        url = f"https://api.gios.gov.pl/pjp-api/rest/data/getData/{int(sensor_id)}"
        response = craft_proxy_request(url)
        return response.json()

    except requests.exceptions.RequestException as err:
        logging.error(f"RequestException occurred: {str(err)}")
        return err
    except Exception as err:
        logging.error(f"An error occurred: {str(err)}")
        return err


def gios_get_air(id):
    """Get last air measurements and station name from the given station id."""

    # Check if id is correct.
    try:
        int(id)
    except:
        return ValueError("Id must be an integer.")
    
    # Get all station data
    all = gios_get_all()

    # If gios_get_all() returns an error, return the error.
    if isinstance(all, Exception):
        return all

    # Get station name.
    name_search = [
        station["stationName"] for station in all if station["id"] == int(id)
    ]

    if len(name_search) == 1:
        station_name = name_search[0]
    else:
        return ValueError("Cannot find station name.")

    # Get sensors data
    sensors = gios_get_sensors(int(id))

    # If gios_get_sensors() returns an error, return the error.
    if isinstance(sensors, Exception):
        return sensors
    
    # API returns empty list if sensor ID is invalid
    if isinstance(sensors, list) and not all:
        return ValueError("Wrong sensor id.")

    sensors_id_list = [sensor["id"] for sensor in sensors]
    measures_data_list = [gios_get_data(sensor_id) for sensor_id in sensors_id_list]

    # Parse data
    def last_read(o):
        """Get last non empty reading from measuring data."""
        # If list of values is empty return dict with key name and "no data" string.
        if len(o["values"]) == 0:
            return {"key": o["key"], "value": "no data", "date": "no data"}

        # Traverse list of dicts with values, pass all None values, return last actual value.
        for v in o["values"]:
            if v["value"] == None:
                pass
            else:
                return {"key": o["key"], "value": v["value"], "date": v["date"]}

    readings = [last_read(i) for i in measures_data_list]

    return [readings, station_name]


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        f"This is Air Bot PL\nversion: {version} \nType /help to see all commands",
    )


help_message = "/all - list ids and names of all available stations\n\n\
type 'air id' - get air measurement from the given station id; e.g.: 'air 10955'\n\n\
type 'loc latitude longitude' - get air measurement from station closest to given coordinates; e.g.: 'loc 54.35 18.6667'\n\n\
share location - get air measurement from station closest to shared location\n\n\
/types - get types of measurement and norms\n\n\
/help - get this message"


@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, help_message)


@bot.message_handler(commands=["types"])
def types(message):
    bot.send_message(
        message.chat.id,
        "PM10 - particulate matter 10, inhalable particles, with diameters that are generally 10 micrometers and smaller; norm: 50 μg/m3/year\n\n\
PM2.5 - particulate matter 2.5 fine inhalable particles, with diameters that are generally 2.5 micrometers and smaller; norm 20 μg/m3/year\n\n\
CO - carbon monoxide; norm: 10 000 μg/m3/8 hour\n\n\
SO2 - sulfur dioxide; norm: 350 μg/m3/1 hour\n\n\
NO2 - nitrogen dioxide; norm: 200 μg/m3/1 hour\n\n\
C6H6 - benzene; norm: 5 μg/m3/year\n\n\
O3 - ozone; norm: 120 μg/m3/8 hour\n\n\
Norms: Polish Chief Inspectorate for Environmental Protection; www.gios.gov.pl\n\n\
Units: microgram / cubic meter / averaging period",
    )


@bot.message_handler(commands=["all"])
def all(message):
  # Sending a "typing" "animation" during the process.
    bot.send_chat_action(message.chat.id, "typing")
    
    # Get all station data
    all = gios_get_all()

    # Check what was returned by gios_get_all(), if it is an exception send an error message.
    if isinstance(all, requests.exceptions.RequestException):
        bot.reply_to(message, f"Request problem occurred. Please try again later.")

    elif isinstance(all, Exception):
        bot.reply_to(message, f"Unkown problem occurred during the process.")

    # API returns empty list if ID is invalid 
    elif isinstance(all, list) and not all:
        bot.reply_to(message, "List is empty, please try again later.")
    else:
        # Parse response
        all_stations = [f'{station["stationName"]} id: {station["id"]}' for station in all]
        all_stations_string = " | ".join(map(str, all_stations))

        # Send message, slice if needed
        try:
            bot.reply_to(message, all_stations_string)
        except:
            for part in long_msg(all_stations_string):
                bot.reply_to(message, part)


@bot.message_handler(func=air_command_test)
def air(message):
    # Sending a "typing" "animation" during the process.
    bot.send_chat_action(message.chat.id, "typing")

    id = message.text.split()[1]

    response = gios_get_air(id)
   
    # Check what was returned by gios_get_air(id), if it is an ValueError send an error message.
    if isinstance(response, ValueError):
        bot.reply_to(message, f"Wrong id.")
    
    elif isinstance(response, requests.exceptions.RequestException):
        bot.reply_to(message, f"Request problem occurred. Please try again later.")
    
    elif isinstance(response, Exception):
        bot.reply_to(message, f"Unkown problem occurred during the process.")

    # API returns empty list if ID is invalid 
    elif isinstance(response, list) and not all:
        bot.reply_to(message, "List is empty, please try again later.")

    else:
        readings = response[0]
        station_name = response[1]

        # If list of readings is empty send error message.
        if not readings:
            bot.reply_to(message, "Redings are empty.")
        # Send message with formatted readings.
        else:
            html_message = (
                f"{station_name}\n"
                f"<pre>{msg_string_format(readings)}</pre>"
            )

            bot.reply_to(
                message,
                html_message, parse_mode='HTML')


@bot.message_handler(func=loc_command_test)
def loc(message):
    # Sending a "typing" "animation" during the process.
    bot.send_chat_action(message.chat.id, "typing")

    latitude = message.text.split()[1]
    longitude = message.text.split()[2]

    # Check if both arguments are floats.
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except:
        bot.reply_to(message, "Wrong location.")
        return

    # Check if latitude and longitude are in (-90, 90) range.
    if not -90.0 <= latitude <= 90.0 or not -90.0 <= longitude <= 90.0:
        bot.reply_to(message, "Wrong location.")
        return

    user_location = (latitude, longitude)

    # Get a dict of ids and distances.
    distances = gios_distance(user_location)

    # Check what was returned by gios_get_all(), if it is an exception send an error message.
    if isinstance(distances, requests.exceptions.RequestException):
        bot.reply_to(message, f"Request problem occurred. Please try again later.")

    elif isinstance(distances, Exception):
        bot.reply_to(message, f"Unkown problem occurred during the process.")

    else:

        # Sort dict by distance. item[1] - sorting is based on the values of the dictionary.
        distances_sorted = dict(sorted(distances.items(), key=lambda item: item[1]))

        closest_station_id = list(distances_sorted.keys())[0]
        closest_station_distance = round(list(distances_sorted.values())[0], 2)

        readings, station_name = gios_get_air(closest_station_id)

        # If list of readings is empty send error message.
        if not readings:
            bot.reply_to(message, "Redings are empty.")
        # Send message with formatted readings.
        else:
            html_message = (
                f"{station_name}\n"
                f"ID: {closest_station_id}\n"
                f"Distance: {closest_station_distance} km\n"
                f"<pre>{msg_string_format(readings)}</pre>"
            )

            bot.reply_to(
                message,
                html_message, parse_mode='HTML')
             

@bot.message_handler(content_types=["location"])
def handle_location(message):
    # Sending a "typing" "animation" during the process.
    bot.send_chat_action(message.chat.id, "typing")

    user_location = (message.location.latitude, message.location.longitude)

    # Get a dict of ids and distances.
    distances = gios_distance(user_location)

    # Check what was returned by gios_get_all(), if it is an exception send an error message.
    if isinstance(distances, requests.exceptions.RequestException):
        bot.reply_to(message, f"Request problem occurred. Please try again later.")

    elif isinstance(distances, Exception):
        bot.reply_to(message, f"Unkown problem occurred during the process.")  
    
    else:
        # Sort dict by distance. item[1] - sorting is based on the values of the dictionary.
        distances_sorted = dict(sorted(distances.items(), key=lambda item: item[1]))

        closest_station_id = list(distances_sorted.keys())[0]
        closest_station_distance = round(list(distances_sorted.values())[0], 2)

        readings, station_name = gios_get_air(closest_station_id)

        # If list of readings is empty send error message.
        if not readings:
            bot.reply_to(message, "Redings are empty.")
        # Send message with formatted readings.
        else:
            html_message = (
                f"{station_name}\n"
                f"ID: {closest_station_id}\n"
                f"Distance: {closest_station_distance} km\n"
                f"<pre>{msg_string_format(readings)}</pre>"
            )

            bot.reply_to(
                message,
                html_message, parse_mode='HTML')


@bot.message_handler(commands=["allx"])
def all(message):

    dict = {
        "Widuchowa" : "air 961",
        "Szczecinek, ul. Przemysłowa" : "air 983",
        "Kołobrzeg, ul. Żółkiewskiego" : "air 10934"

    }


    # Creating an inline keyboard
    keyboard = telebot.types.InlineKeyboardMarkup()
    
    # Creating an inline keyboard button with a predefined message
    for item in dict:

        button = telebot.types.InlineKeyboardButton(text=f'{item}', callback_data=dict[item])
        keyboard.add(button)
    
    
    # Sending a message with the inline keyboard
    bot.send_message(message.chat.id, "Press the button to send a predefined message to the bot.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
        bot.send_message(call.message.chat.id, f'{call.data}')


# If all handles above do not fit, help_message will be displayed.
@bot.message_handler()
def start(message):
    bot.send_message(message.chat.id, help_message)


bot.polling()
