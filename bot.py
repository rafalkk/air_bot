import os
import requests
from geopy import distance

#pyTelegramBotAPI
import telebot

#REMEBER TO UPDATE VERSION
version="1.0.4"
#REMEBER TO UPDATE VERSION

API_KEY = os.environ.get("TELEGRAM_BOT_API_KEY")

bot = telebot.TeleBot(API_KEY)


def msg_string_format(list):
    """
    Takes list of readings. Format value to two decimal points.
    If the value is equal to "no data", it means that there were no values to read.
    """
    raw_string = ""
    for i in list:
        if i["value"] == "no data":
            raw_string = raw_string + f'{i["key"]} : {i["value"]}' + "\n"
        else:
            raw_string = raw_string + f'{i["key"]} : {i["value"]:.2f}' + "\n"
    return raw_string


def long_msg(msg, max_char=4096):
    """
    Takes string and return a list of smaller strings.
    Defult 4096 is max number of chars in one telegram message.
    """
    return [msg[i:i + max_char] for i in range(0, len(msg), max_char)]


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
    all = gios_get_all()
    distances = {station["id"]: distance.great_circle(user_location, (station["gegrLat"], station["gegrLon"])).km for station in all}
    return distances


def gios_get_all():
    """Get a list and info of all air measurement stations."""
    # Contact API
    try:
        url = "https://api.gios.gov.pl/pjp-api/rest/station/findAll"
        response = requests.get(url)
        response_json = response.json()

    except:
        return None

    return response_json


def gios_get_sensors(station_id):
    """Get a list of measuring sensors from a given id of measurement station."""
    # Contact API
    try:
        url = f"https://api.gios.gov.pl/pjp-api/rest/station/sensors/{int(station_id)}"
        response = requests.get(url)
        response_json = response.json()

    except:
        return None

    return response_json


def gios_get_data(sensor_id):
    """Get measuring data form a given id of sensor id."""
    # Contact API
    try:
        url = f"https://api.gios.gov.pl/pjp-api/rest/data/getData/{int(sensor_id)}"
        response = requests.get(url)
        response_json = response.json()

    except:
        return None

    return response_json


def gios_get_air(id):

    # Check if id is correct and get station name
    all = gios_get_all()
    name_search = [station["stationName"] for station in all if station["id"] == int(id)]
    if len(name_search) == 1:
        station_name = name_search[0]
    else:
        raise ValueError("wrong id")

    # Get data
    sensors = gios_get_sensors(int(id))
    sensors_id_list = [sensor["id"] for sensor in sensors]
    meas_data_list = [gios_get_data(sensor_id) for sensor_id in sensors_id_list]

    # Parse data
    def last_read(o):
        """ Get last non empty reading from measuring data."""
        #if list of values is empty return dict with key name and "no data" string
        if len(o["values"]) == 0:
            return {"key" : o["key"],
            "value" : "no data",
            "date" : "no data"}

        #traverse list of dicts with values, pass all None values, return last actual value
        for v in o["values"]:
            if v["value"] == None:
                pass
            else:
                return {"key" : o["key"],
                        "value" : v["value"],
                        "date" : v["date"]}

    readings = [last_read(i) for i in meas_data_list]
    return readings, station_name


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f"This is Air Bot PL\nversion: {version} \nType /help to see all commands")


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
    bot.send_message(message.chat.id, "PM10 - particulate matter 10, inhalable particles, with diameters that are generally 10 micrometers and smaller; norm: 50 μg/m3/year\n\n\
PM2.5 - particulate matter 2.5 fine inhalable particles, with diameters that are generally 2.5 micrometers and smaller; norm 20 μg/m3/year\n\n\
CO - carbon monoxide; norm: 10 000 μg/m3/8 hour\n\n\
SO2 - sulfur dioxide; norm: 125 μg/m3/day\n\n\
NO2 - nitrogen dioxide; norm: 40 μg/m3/year\n\n\
C6H6 - benzene; norm: 5 μg/m3/year\n\n\
O3 - ozone; norm: 120 μg/m3/8 hour\n\n\
Norms: Polish Chief Inspectorate for Environmental Protection; www.gios.gov.pl\n\n\
Units: microgram / cubic meter / averaging period")


@bot.message_handler(commands=["all"])
def all(message):
    all = gios_get_all()
    # Parse response
    all_stations = [f'{station["stationName"]} id: {station["id"]}' for station in all]
    all_stations_string = ' | '.join(map(str, all_stations))

    # Send message, slice if needed
    try:
        bot.reply_to(message, all_stations_string)
    except:
        for part in long_msg(all_stations_string):
            bot.reply_to(message, part)


@bot.message_handler(func = air_command_test)
def air(message):
    id = message.text.split()[1]

    # Check id
    try:
        int(id)
        gios_get_air(id)
    except:
        bot.reply_to(message, "wrong id")
        return

    readings, station_name = gios_get_air(id)

    # Send message if list of readings is not empty
    if not readings:
        bot.reply_to(message, "redings are empty")
    else:
        readings_string = msg_string_format(readings)

        bot.reply_to(message, f"{station_name}\n{readings_string}")


@bot.message_handler(func = loc_command_test)
def loc(message):
    latitude = message.text.split()[1]
    longitude = message.text.split()[2]

    # Check if both arguments are floats
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except:
        bot.reply_to(message, "wrong location")
        return

    # Check if latitude and longitude are in (-90, 90) range
    if not -90.0 <= latitude <= 90.0 or not -90.0 <= longitude <= 90.0:
        bot.reply_to(message, "wrong location")
        return

    user_location = (latitude, longitude)

    # get a dict of ids and distances
    distances = gios_distance(user_location)
    # sort dict by distance
    distances_sorted = dict(sorted(distances.items(), key=lambda item: item[1]))

    closest_station_id = list(distances_sorted.keys())[0]
    closest_station_distance = round(list(distances_sorted.values())[0], 2)

    readings, station_name = gios_get_air(closest_station_id)

    # Send message if list of readings is not empty
    if not readings:
        bot.reply_to(message, "redings are empty")
    else:
        readings_string = msg_string_format(readings)

        bot.reply_to(message, f"{station_name}\ndistance: {closest_station_distance} km\n{readings_string}")


@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_location = (message.location.latitude, message.location.longitude)

    # get a dict of ids and distances
    distances = gios_distance(user_location)
    # sort dict by distance
    distances_sorted = dict(sorted(distances.items(), key=lambda item: item[1]))

    closest_station_id = list(distances_sorted.keys())[0]
    closest_station_distance = round(list(distances_sorted.values())[0], 2)

    readings, station_name = gios_get_air(closest_station_id)

    # Send message if list of readings is not empty
    if not readings:
        bot.reply_to(message, "redings are empty")
    else:
        readings_string = msg_string_format(readings)

        bot.reply_to(message, f"{station_name}\ndistance: {closest_station_distance} km\n{readings_string}")


# If all handles above do not fit, help_message will be displayed
@bot.message_handler()
def start(message):
    bot.send_message(message.chat.id, help_message)

bot.polling()

