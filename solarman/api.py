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
        self.inverter_id: int = 0
        self.logger_id: int = 0

        station_id = self.get_station()
        logging.info(f"Configured station: {self.station_id}\tAPI retrieved station: {station_id}")
        # TODO: use retrieved ID if it works

        self.station_device_list = self.get_station_device_list()

        self.get_data()

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

    def get_station(self):
        """
        Return station realtime data
        :return: realtime data
        """
        try:
            response = requests.post(
                url = self.url_base + "/station/v1.0/list",
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "bearer " + self.token,
                },
                data = json.dumps({"page": 99})
            )
            data = json.loads(response.content)
            logging.info(f"station list: {data}")
            if not data["stationList"]:
                logging.error("Unable to find stationList")
            
            station_list = data["stationList"]

            if len(station_list)>1:
                logging.warning("Found more than one station.  Using first.")
            return data["stationList"][0]["id"]

        except requests.exceptions.RequestException as error:
            logging.error(error)


    def get_station_device_list(self):
        """Find the inverter and logger IDs."""
        try:
            response = requests.post(
                url = self.url_base + "/station/v1.0/device",
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "bearer " + self.token,
                },
                data = json.dumps({"stationId": self.station_id})
            )
            data = json.loads(response.content)
            logging.info(f"station_device_list data: {data}")

            device_list = data["deviceListItems"]
            for device in device_list:
                if device["deviceType"]=="INVERTER":
                    self.inverter_id = int(device["deviceId"])
                if device["deviceType"]=="COLLECTOR":
                    self.logger_id = int(device["deviceId"])
                

        except requests.exceptions.RequestException as error:
            logging.error(error)

    def get_data(self):
        """Get recurring data."""
        self.station_realtime = self.get_station_realtime()

        self.device_current_data_inverter = self.get_device_current_data(
            self.config["inverterId"],
            self.inverter_id
        )
        self.device_current_data_logger = self.get_device_current_data(
            self.config["loggerId"],
            self.logger_id
        )
        

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
            logging.error(error)

    def get_device_current_data(self, device_sn: str, device_id: int):
        """
        Return device current data
        :return: current data
        """
        if device_id == 0:
            data = {"deviceId": device_id}
        else:
            data = {"deviceSn":device_sn,"deviceId": device_id}


        try:
            response = requests.post(
                url = self.url_base + "/device/v1.0/currentData?language=en",
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "bearer " + self.token,
                },
                data = json.dumps(data)
            )
            data = json.loads(response.content)
            logging.info(f"current_data:\n{data}")
            return data

        except requests.exceptions.RequestException as error:
            logging.error(error)


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
