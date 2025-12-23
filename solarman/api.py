"""
Api
"""

import http.client
import requests
import json
import logging
import sys


class SolarmanApi:
    """
    Connect to the Solarman API and return PV data
    """

    def __init__(self, config):
        self.config = config
        self.station_id = config["stationId"]
        self.url = config["url"]
        self.url_base = "https://" + self.url
        self.token = self.get_token(
            self.config["appid"],
            self.config["secret"],
            self.config["username"],
            self.config["passhash"],
        )
        self.station_realtime = self.get_station_realtime()
        self.device_current_data_inverter = self.get_device_current_data(
            self.config["inverterId"]
        )
        self.device_current_data_logger = self.get_device_current_data(
            self.config["loggerId"]
        )

        try:
            self.device_current_data_meter = self.get_device_current_data(
                self.config["meterId"]
            )
        except KeyError:
            self.device_current_data_meter = None

    def get_token(self, appid, secret, username, passhash):
        """
        Get a token from the API
        :return: access_token
        """
        try:
            conn = http.client.HTTPSConnection(self.url, timeout=60)
            payload = json.dumps(
                {"appSecret": secret, "email": username, "password": passhash}
            )
            headers = {"Content-Type": "application/json"}
            url = f"/account/v1.0/token?appId={appid}&language=en"
            conn.request("POST", url, payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read())
            logging.debug("Received token")
            return data["access_token"]
        except Exception as error:  # pylint: disable=broad-except
            logging.error("Unable to fetch token: %s", str(error))
            sys.exit(1)

    def get_station_realtime(self):
        """
        Return station realtime data
        :return: realtime data
        """
        try:
            response = requests.post(
                url = self.url_base + "/station/v1.0/realTime?language=en",
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "bearer " + self.token,
                },
                data = json.dumps({"stationId": self.station_id})
            )
            print(f'Response HTTP Status Code: {response.status_code}')
            print(f'Response HTTP Response Body: {response.content}')            
            data = json.loads(response.content)
            print(f"data:\n{data}")
            return data

        except requests.exceptions.RequestException as error:
            print(error)

    def get_device_current_data(self, device_sn):
        """
        Return device current data
        :return: current data
        """
        try:
            response = requests.post(
                url = self.url_base + "/device/v1.0/currentData?language=en",
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "bearer " + self.token,
                },
                data = json.dumps({"deviceSn": device_sn})
            )
            print(f'Response HTTP Status Code: {response.status_code}')
            print(f'Response HTTP Response Body: {response.content}')            
            data = json.loads(response.content)
            print(f"data:\n{data}")
            return data

        except requests.exceptions.RequestException as error:
            print(error)


class ConstructData:  # pylint: disable=too-few-public-methods
    """
    Return restructured and separated device current data
    Original data is removed
    :return: new current data
    """

    def __init__(self, data):
        self.data = data
        self.device_current_data = {}
        try:
            for i in self.data["dataList"]:
                del i["key"]
                name = i["name"]
                name = name.replace(" ", "_")
                del i["name"]
                self.device_current_data[name] = i["value"]
            del self.data["dataList"]
        except KeyError:
            pass
