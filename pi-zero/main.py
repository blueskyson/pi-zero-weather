from time import sleep
from nextion import Nextion
import requests


def main():
    nextion = Nextion(port="COM3", baudrate=9600)
    try:
        while True:
            commands = nextion.getCommands()
            if len(commands) > 0:
                for command in commands:
                    pass
            else:
                sleep(0.03)
    except KeyboardInterrupt:
        print("Program terminated.")
    finally:
        nextion.close()


def parse(buffer):
    messages = buffer.split(b'\xFF\xFF\xFF')
    if buffer[-3:] == b'\xFF\xFF\xFF':
        return b'', messages[:-1]
    return messages[-1], messages[:-1]


def processMessages(messages, ser):
    for message in messages:
        print(message)
        # if message[0] != 0x65:
        #     return
        # page_id = message[1]
        # component_id = message[2]
        # touch_type = message[3]
        # if page_id == 0x1 and component_id == 0x8:
        #     updateWeather(ser)
        # elif page_id == 0x0 and component_id == 0x2:
        #     GPIO.output(17, GPIO.HIGH)
        # elif page_id == 0x0 and component_id == 0x3:
        #     GPIO.output(17, GPIO.LOW)


# def updateWeather(ser):
#     temperature, humidity = get_weather_data()
#     print("Temperature:", temperature, "Humidity:", humidity)
#     command = ''
#     command += f'tTempC.txt="{temperature}"\xFF\xFF\xFF'
#     command += f'tTempF.txt="{int(temperature * 1.8 + 32)}"\xFF\xFF\xFF'
#     command += f'tHumidity.txt="{int(humidity)}"\xFF\xFF\xFF'
#     command += f'jHumidity.val={int(humidity)}\xFF\xFF\xFF'
#     ser.write(command.encode('iso-8859-1'))


# def get_weather_data():
#     url = "https://api.open-meteo.com/v1/forecast"
#     params = {
#         "latitude": 34.052235,
#         "longitude": -118.243683,
#         "current": "temperature_2m,relative_humidity_2m"
#     }

#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         data = response.json()
#         current_weather = data.get("current", {})
#         temperature = current_weather.get("temperature_2m")
#         humidity = current_weather.get("relative_humidity_2m")
#         return temperature, humidity
#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching weather data: {e}")
#         return 0.0, 0.0

if __name__ == "__main__":
    main()