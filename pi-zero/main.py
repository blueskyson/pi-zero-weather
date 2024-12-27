from time import sleep
from datetime import datetime
from nextion import Nextion
from network import NetworkManager
from external_api import ApiClient

# Map to Nextion Picture ID
WEATHER_IMAGE = {
    0: 1,
    1: 1,
    2: 2,
    3: 3,
    45: 9,
    48: 9,
    51: 6,
    53: 6,
    55: 6,
    56: 8,
    57: 8,
    61: 5,
    63: 5,
    65: 5,
    66: 5,
    67: 5,
    71: 8,
    73: 8,
    75: 8,
    77: 8,
    80: 5,
    81: 5,
    82: 5,
    85: 8,
    86: 8,
    95: 7,
    96: 7,
    99: 7
}

# Increment by 9 for Picture ID
WEATHER_IMAGE_SMALL = {key: value + 9 for key, value in WEATHER_IMAGE.items()}

# Global variables
nextion = Nextion(port="/dev/serial0", baudrate=9600)
nm = NetworkManager()
nm.print_device_info()
api = ApiClient()
ip_info = api.get_ip_info()
geocode = None

ap_list = []
setting_selected_row = -1
setting_ssid_page = 0
setting_unit_of_temp = 'fahrenheit'

# Flag for fetching string data after user push buttons
is_password = False
is_location = False


def main():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nextion.send('sendme\xFF\xFF\xFF')
    try:
        while True:
            commands = nextion.getCommands()
            if len(commands) > 0:
                for cmd in commands:
                    processCommand(cmd)
            else:
                new_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if new_time != current_time:
                    current_time = new_time
                    nextion.send(f'tDatetime.txt="{current_time}"\xFF\xFF\xFF', False)
                sleep(0.03)
    except KeyboardInterrupt:
        print("Program terminated.")
    finally:
        nextion.close()
        print("Bye.")


def processCommand(cmd):
    global setting_selected_row, setting_unit_of_temp, is_password, is_location
    if cmd.event is nextion.CURRENT_PAGE_NUMBER:
        if cmd.page is nextion.PAGE_MAIN:
            show_main()
        elif cmd.page is nextion.PAGE_MENU:
            show_menu()
        return

    if cmd.page is nextion.PAGE_MAIN:
        match cmd.component:
            case nextion.B_MENU:
                show_menu()
            case nextion.B_REFRESH:
                nextion.send(f'page pageMain\xFF\xFF\xFF') # Erase charts and reset main page
                show_main()
    elif cmd.page is nextion.PAGE_MENU:
        match cmd.component:
            case nextion.B_LEFT:
                show_prev_ssid_page()
            case nextion.B_RIGHT:
                show_next_ssid_page()
            case nextion.T_ID1:
                select_row(0)
            case nextion.T_ID2:
                select_row(1)
            case nextion.T_ID3:
                select_row(2)
            case nextion.T_ID4:
                select_row(3)
            case nextion.T_ID5:
                select_row(4)
            case nextion.T_SSID1:
                select_row(0)
            case nextion.T_SSID2:
                select_row(1)
            case nextion.T_SSID3:
                select_row(2)
            case nextion.T_SSID4:
                select_row(3)
            case nextion.T_SSID5:
                select_row(4)
            case nextion.B_CONNECT:
                nextion.send("get tPassword.txt\xFF\xFF\xFF")
                is_password = True
            case nextion.B_UPDATE_LOCATION:
                nextion.send("get tLocation.txt\xFF\xFF\xFF")
                is_location = True
            case nextion.B_UNIT_TEMP:
                if setting_unit_of_temp == "fahrenheit":
                    setting_unit_of_temp = "celsius"
                else:
                    setting_unit_of_temp = "fahrenheit"
                nextion.send(f'bUnitTemp.txt="Unit of Temperature: {setting_unit_of_temp}"\xFF\xFF\xFF')
            case nextion.B_BACK:
                show_main()
    elif cmd.page == -1:
        if cmd.string_data is not None:
            handle_string_data(cmd.string_data)


def show_main():
    global ip_info, geocode, setting_ssid_page, setting_selected_row, ap_list
    # Reset menu settings
    setting_ssid_page = 0
    setting_selected_row = -1
    ap_list = []
    
    if geocode is not None:
        nextion.send(f'tAddress.txt="{geocode.city}, {geocode.country_code.upper()}"\xFF\xFF\xFF')
        update_weather(geocode.lat, geocode.lng, ip_info.timezone)
        return

    if ip_info is not None:
        nextion.send(f'tAddress.txt="{ip_info.city}, {ip_info.region}, {ip_info.country}"\xFF\xFF\xFF')
        update_weather(ip_info.lat, ip_info.lng, ip_info.timezone)
        return

    nextion.send(f'tAddress.txt="NO WI-FI"\xFF\xFF\xFF')


def show_menu():
    global setting_ssid_page, setting_unit_of_temp, ap_list
    nm.request_scan()
    ap_list = nm.get_access_points()
    instruction = get_ssids(setting_ssid_page * 5)
    instruction += f'bUnitTemp.txt="Unit of Temperature: {setting_unit_of_temp}"\xFF\xFF\xFF'
    nextion.send(instruction)


def show_prev_ssid_page():
    global setting_ssid_page, setting_selected_row
    if setting_ssid_page == 0:
        return
    setting_ssid_page = setting_ssid_page - 1
    setting_selected_row = -1
    instruction = get_ssids(setting_ssid_page * 5)
    nextion.send(instruction)


def show_next_ssid_page():
    global setting_ssid_page, setting_selected_row, ap_list
    if (setting_ssid_page + 1) * 5 >= len(ap_list):
        return
    setting_ssid_page = setting_ssid_page + 1
    setting_selected_row = -1
    instruction = get_ssids(setting_ssid_page * 5)
    nextion.send(instruction)


def handle_string_data(data):
    global ip_info, geocode, setting_selected_row, setting_ssid_page, ap_list, is_password, is_location
    if is_password:
        is_password = False
        if setting_selected_row == -1:
            print("Failed to connect. No SSID is selected.")
            return
        ssid = ap_list[setting_ssid_page * 5 + setting_selected_row].ssid
        print(f"Start connecting {ssid}")
        nm.add_connection(ssid, data)
        show_menu()
 
        for i in range(5):
            sleep(2)
            ip_info = api.get_ip_info()
            if ip_info is not None:
                break

        if ssid != nm.get_current_ssid():
            print("Failed to connect.")
            return
    elif is_location:
        is_location = False
        geocode = api.get_geocode(data)
        if geocode is not None:
            print("Update location:", geocode.city, geocode.country)

        
def select_row(row):
    global setting_selected_row
    instruction = ""
    match setting_selected_row:
        case 0:
            instruction += f'tSSID1.bco=65535\xFF\xFF\xFF'
        case 1:
            instruction += f'tSSID2.bco=65535\xFF\xFF\xFF'
        case 2:
            instruction += f'tSSID3.bco=65535\xFF\xFF\xFF'
        case 3:
            instruction += f'tSSID4.bco=65535\xFF\xFF\xFF'
        case 4:
            instruction += f'tSSID5.bco=65535\xFF\xFF\xFF'
    match row:
        case 0:
            instruction += f'tSSID1.bco=65504\xFF\xFF\xFF'
        case 1:
            instruction += f'tSSID2.bco=65504\xFF\xFF\xFF'
        case 2:
            instruction += f'tSSID3.bco=65504\xFF\xFF\xFF'
        case 3:
            instruction += f'tSSID4.bco=65504\xFF\xFF\xFF'
        case 4:
            instruction += f'tSSID5.bco=65504\xFF\xFF\xFF'
    setting_selected_row = row
    nextion.send(instruction)


def get_ssids(first):
    global ap_list
    active_ssid = nm.get_current_ssid()
    instruction = ""

    instruction += f'tId1.txt="{first + 1:02}"\xFF\xFF\xFF'
    if first < len(ap_list):
        instruction += f'tSSID1.txt="{ap_list[first].strength_bars:5} {ap_list[first].ssid}"\xFF\xFF\xFF'
        if ap_list[first].ssid == active_ssid:
            instruction += f'tSSID1.bco=2032\xFF\xFF\xFF'
        else:
            instruction += f'tSSID1.bco=65535\xFF\xFF\xFF'
    else:
        instruction += f'tSSID1.txt="--"\xFF\xFF\xFF'
    
    instruction += f'tId2.txt="{first + 2:02}"\xFF\xFF\xFF'
    if first + 1 < len(ap_list):
        instruction += f'tSSID2.txt="{ap_list[first + 1].strength_bars:5} {ap_list[first + 1].ssid}"\xFF\xFF\xFF'
        if ap_list[first + 1].ssid == active_ssid:
            instruction += f'tSSID2.bco=2032\xFF\xFF\xFF'
        else:
            instruction += f'tSSID2.bco=65535\xFF\xFF\xFF'
    else:
        instruction += f'tSSID2.txt="--"\xFF\xFF\xFF'

    instruction += f'tId3.txt="{first + 3:02}"\xFF\xFF\xFF'
    if first + 2 < len(ap_list):
        instruction += f'tSSID3.txt="{ap_list[first + 2].strength_bars:5} {ap_list[first + 2].ssid}"\xFF\xFF\xFF'
        if ap_list[first + 2].ssid == active_ssid:
            instruction += f'tSSID3.bco=2032\xFF\xFF\xFF'
        else:
            instruction += f'tSSID3.bco=65535\xFF\xFF\xFF'
    else:
        instruction += f'tSSID3.txt="--"\xFF\xFF\xFF'

    instruction += f'tId4.txt="{first + 4:02}"\xFF\xFF\xFF'
    if first + 3 < len(ap_list):
        instruction += f'tSSID4.txt="{ap_list[first + 3].strength_bars:5} {ap_list[first + 3].ssid}"\xFF\xFF\xFF'
        if ap_list[first + 3].ssid == active_ssid:
            instruction += f'tSSID4.bco=2032\xFF\xFF\xFF'
        else:
            instruction += f'tSSID4.bco=65535\xFF\xFF\xFF'
    else:
        instruction += f'tSSID4.txt="--"\xFF\xFF\xFF'

    instruction += f'tId5.txt="{first + 5:02}"\xFF\xFF\xFF'
    if first + 4 < len(ap_list):
        instruction += f'tSSID5.txt="{ap_list[first + 4].strength_bars:5} {ap_list[first + 4].ssid}"\xFF\xFF\xFF'
        if ap_list[first + 4].ssid == active_ssid:
            instruction += f'tSSID5.bco=2032\xFF\xFF\xFF'
        else:
            instruction += f'tSSID5.bco=65535\xFF\xFF\xFF'
    else:
        instruction += f'tSSID5.txt="--"\xFF\xFF\xFF'

    return instruction


def update_weather(lat, lng, timezone = ""):
    global setting_unit_of_temp
    weatherData = api.get_weather(lat, lng, timezone, setting_unit_of_temp)
    if weatherData is None:
        nextion.send(f'tAddress.txt="Error fetching weather"\xFF\xFF\xFF')
        return
    current = weatherData.current
    cur_units = weatherData.current_units
    daily = weatherData.daily
    imgId = WEATHER_IMAGE[current.weather_code]
    
    # Current weather
    instruction = ''
    instruction += f'pWeather.pic={imgId}\xFF\xFF\xFF'
    instruction += f'tWeather.txt="{current.weather_description}"\xFF\xFF\xFF'
    instruction += f'tTemperature.txt="{current.temperature}{cur_units.temperature}"\xFF\xFF\xFF'
    instruction += f'tPrecipitation.txt="{daily[0].precipitation_probability}%"\xFF\xFF\xFF'
    instruction += f'tHumidity.txt="{current.humidity}%"\xFF\xFF\xFF'
    instruction += f'tUVIndex.txt="{daily[0].uv_index}"\xFF\xFF\xFF'
    instruction += f'tSunrise.txt="{daily[0].sunrise.strftime("%H:%M")}"\xFF\xFF\xFF'
    instruction += f'tSunset.txt="{daily[0].sunset.strftime("%H:%M")}"\xFF\xFF\xFF'
    nextion.send(instruction)

    # 5-day bar chart
    instruction = ''
    chart_left, chart_top = 50, 440
    bar_width = 20
    chart_width, chart_height = 380, 180
    chart_bottom = chart_top + chart_height + 40
    bar_space = chart_width // 5
    bar_margin = (bar_space - bar_width) // 2
    max_temp = max(d.temperature_max for d in daily)
    min_temp = min(d.temperature_min for d in daily)
    temp_range = max_temp - min_temp
    scale = chart_height / temp_range if temp_range > 0 else 1
    for i in range(5):
        left = chart_left + i * bar_space
        top = chart_top + chart_height - int((daily[i].temperature_max - min_temp) * scale)
        height = int((daily[i].temperature_max - daily[i].temperature_min) * scale)
        instruction += f'fill {left + bar_margin},{top},{bar_width},{height},{65120}\xFF\xFF\xFF'
        instruction += f'xstr {left},{top - 30},{bar_space},30,3,WHITE,0,1,1,0," {int(daily[i].temperature_max)}°"\xFF\xFF\xFF'
        instruction += f'xstr {left},{top + height},{bar_space},30,3,WHITE,0,1,1,0," {int(daily[i].temperature_min)}°"\xFF\xFF\xFF'
    instruction += f'line {chart_left},{chart_bottom},{chart_left + chart_width},{chart_bottom},{31727}\xFF\xFF\xFF'
    nextion.send(instruction)

    # 5-day weather picture
    instruction = ''
    pic_left, pic_top, pic_width = chart_left, chart_bottom + 20, 50
    pic_margin = (bar_space - pic_width) // 2
    for i in range(5):
        left = pic_left + i * bar_space
        pic_id = WEATHER_IMAGE_SMALL[daily[i].weather_code]
        date = daily[i].date.strftime("%a %d")
        instruction += f'pic {left + pic_margin},{pic_top},{pic_id}\xFF\xFF\xFF'
        instruction += f'xstr {left},{pic_top + pic_width + 10},{bar_space},30,3,WHITE,0,1,1,0,"{date}"\xFF\xFF\xFF'
    nextion.send(instruction)


if __name__ == "__main__":
    main()
