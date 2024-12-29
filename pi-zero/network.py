import gi
import time
import math
import re
from dataclasses import dataclass
gi.require_version("NM", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, NM

@dataclass
class AccessPointInfo:
    dbus_path: str
    ssid: str
    bssid: str
    last_seen: int
    frequency: int
    channel: int
    mode: str
    flags: str
    wpa_flags: str
    rsn_flags: str
    security: str
    strength: int
    strength_bars: str
    is_active_ap: bool = False


class NetworkManager:
    NM80211Mode = getattr(NM, "80211Mode")
    NM80211ApFlags = getattr(NM, "80211ApFlags")
    NM80211ApSecurityFlags = getattr(NM, "80211ApSecurityFlags")
    SCAN_THRESHOLD_MSEC = 500


    def __init__(self):
        self.client = NM.Client.new(None)
        self.main_loop = GLib.MainLoop()
        self.device = None
        for device in self.client.get_devices():
            if device.get_device_type() == NM.DeviceType.WIFI:
                self.device = device
                break
        
        if not self.device:
            raise RuntimeError("No WIFI device found.")
 

    def print_device_info(self):
        if self.device is None:
            last_scan = "device disappeared"
        else:
            t = self.device.get_last_scan()
            if t == 0:
                last_scan = "no scan completed"
            else:
                t = (NM.utils_get_timestamp_msec() - t) / 1000.0
                last_scan = f"{t:.2f} sec ago"
                if self.device_needs_scan():
                    last_scan += " (stable)"

        ap = self.device.get_active_access_point()
        if ap is None:
            active_ap = "none"
        else:
            active_ap = f"{self.ap_get_ssid(ap)} ({ap.get_path()})"
        
        print(f"Client ver: {self.client.get_version()}")
        print(f"Device:     {self.device.get_iface()}")
        print(f"State:      {self.device.get_state().value_nick}")
        print(f"D-Bus path: {NM.Object.get_path(self.device)}")
        print(f"Driver:     {self.device.get_driver()}")
        print(f"Active AP:  {active_ap}")
        print(f"Last scan:  {last_scan}")

    
    def get_current_ssid(self):
        ap = self.device.get_active_access_point()
        if ap is None:
            return None
        return self.ap_get_ssid(ap)


    def request_scan(self):
        if not self.device_needs_scan():
            return

        print("Requesting Wi-Fi scan...")
        self.device.request_scan_async(None)
        
        def cb():
            self.main_loop.quit()

        timeout_source = GLib.timeout_source_new(10 * 1000)
        timeout_source.set_callback(cb)
        timeout_source.attach(self.main_loop.get_context())

        def cb(device, prop):
            if not self.device_needs_scan():
                self.main_loop.quit()

        self.device.connect("notify", cb)
        self.main_loop.run()
        timeout_source.destroy()
        print("Finished Wi-Fi scan")


    def get_access_points(self):
        ap_list = []
        active_ap = self.ap_get_ssid(self.device.get_active_access_point())
        for ap in self.device.get_access_points():
            strength = ap.get_strength()
            frequency = ap.get_frequency()
            flags = ap.get_flags()
            wpa_flags = ap.get_wpa_flags()
            rsn_flags = ap.get_rsn_flags()

            t = ap.get_last_seen()
            if t < 0:
                last_seen = "never"
            else:
                t = time.clock_gettime(time.CLOCK_BOOTTIME) - t
                last_seen = "%s sec ago" % (math.ceil(t),)

            ap_info = AccessPointInfo(
                dbus_path = ap.get_path(),
                ssid = self.ap_get_ssid(ap),
                bssid = ap.get_bssid(),
                last_seen = last_seen,
                frequency = frequency,
                channel = NM.utils_wifi_freq_to_channel(frequency),
                mode = self.genum_to_str(self.NM80211Mode, ap.get_mode()),
                flags = self.gflags_to_str(self.NM80211ApFlags, flags),
                wpa_flags = self.gflags_to_str(self.NM80211ApSecurityFlags, wpa_flags),
                rsn_flags = self.gflags_to_str(self.NM80211ApSecurityFlags, rsn_flags),
                security = self.ap_security_flags_to_security(flags, wpa_flags, rsn_flags),
                strength = strength,
                strength_bars = NM.utils_wifi_strength_bars(strength),
            )
            ap_info.is_active_ap = ap_info.ssid == active_ap
            ap_list.append(ap_info)
            print(f"SSID: {ap_info.ssid}, Strength: {ap_info.strength}% | {ap_info.strength_bars}")
        return ap_list


    def add_connection(self, ssid, password):
        connection = NM.SimpleConnection.new()
        ssid_bytes = GLib.Bytes.new(ssid.encode("utf-8"))

        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, "my-wifi-connection")
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, "802-11-wireless")

        s_wifi = NM.SettingWireless.new()
        s_wifi.set_property(NM.SETTING_WIRELESS_SSID, ssid_bytes)
        s_wifi.set_property(NM.SETTING_WIRELESS_MODE, "infrastructure")

        s_wsec = NM.SettingWirelessSecurity.new()
        s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, "wpa-psk")
        s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)

        s_ip4 = NM.SettingIP4Config.new()
        s_ip4.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")

        s_ip6 = NM.SettingIP6Config.new()
        s_ip6.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")
        
        connection.add_setting(s_con)
        connection.add_setting(s_wifi)
        connection.add_setting(s_wsec)
        connection.add_setting(s_ip4)
        connection.add_setting(s_ip6)

        def add_and_activate_cb(client, result, data):
            try:
                ac = client.add_and_activate_connection_finish(result)
                print(f"ActiveConnection {ac.get_path()}")
                print(f"State {ac.get_state().value_nick}")
            except Exception as e:
                print("Error:", e)
            self.main_loop.quit()

        self.client.add_and_activate_connection_async(connection, self.device, None, None, add_and_activate_cb, None)
        self.main_loop.run()


    def device_needs_scan(self):
        if self.device.get_client() is None:
            return False
        t = self.device.get_last_scan()
        return t == 0 or t < NM.utils_get_timestamp_msec() - self.SCAN_THRESHOLD_MSEC
    

    def ap_get_ssid(self, ap):
        if ap is None:
            return "not connected"
        ssid = ap.get_ssid()
        if ssid is None:
            return "no ssid"
        return str(NM.utils_ssid_to_utf8(ssid.get_data()))


    def genum_to_str(self, enum_type, value):
        for n in sorted(dir(enum_type)):
            if not re.search("^[A-Z0-9_]+$", n):
                continue
            enum_value = getattr(enum_type, n)
            if value == enum_value:
                return n
        return f"({value}"


    def gflags_to_str(self, flags_type, value):
        if value == 0:
            return "none"
        str = ""
        for n in sorted(dir(flags_type)):
            if not re.search("^[A-Z0-9_]+$", n):
                continue
            flag_value = getattr(flags_type, n)
            if value & flag_value:
                value &= ~flag_value
                str += " " + n
                if value == 0:
                    break
        if value:
            str += f" (0x{value:0x})"
        return str.lstrip()


    def ap_security_flags_to_security(self, flags, wpa_flags, rsn_flags):
        str = ""
        if (flags & self.NM80211ApFlags.PRIVACY) and (wpa_flags == 0) and (rsn_flags == 0):
            str = str + " WEP"
        if wpa_flags != 0:
            str = str + " WPA1"
        if rsn_flags != 0:
            str = str + " WPA2"
        if (wpa_flags & self.NM80211ApSecurityFlags.KEY_MGMT_802_1X) or (
            rsn_flags & self.NM80211ApSecurityFlags.KEY_MGMT_802_1X
        ):
            str = str + " 802.1X"
        return str.lstrip()
