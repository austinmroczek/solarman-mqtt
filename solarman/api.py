"""
Api
"""

import requests
import json
import logging
import sys
from typing import Optional


class SolarmanApi:
    """
    Connect to the Solarman API and return PV data
    """

    def __init__(self, config):
        self.config = config
        self.url = "https://globalapi.solarmanpv.com"
        self.token = self.get_token(
            self.config["appid"],
            self.config["secret"],
            self.config["username"],
            self.config["passhash"],
        )
        self.inverter_id: int = 0
        self.inverter_sn: str = ''
        self.logger_id: int = 0
        self.logger_sn: str = ''

        logging.info(f"Starting API with URL: {self.url}")

        station_id = self.get_station()
        if station_id == 0:
            self.station_id = int(config["stationId"])
            logging.warning(f"Unable to find useful stationList.  Using configured stationId {self.station_id}")
        else:
            logging.info(f"Using retrieved stationId {station_id}")
            self.station_id = station_id

        self.station_device_list = self.get_station_device_list()

        self.get_data()

    def _make_request(self, url: str, headers: dict, data: dict, operation: str = "request") -> Optional[dict]:
        """
        Centralized request handler with comprehensive error handling.

        :param url: The full URL to request
        :param headers: Request headers
        :param data: Request payload (will be JSON encoded)
        :param operation: Description of the operation for logging
        :return: Response data as dict, or None on error
        """
        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as error:
            logging.error(f"Request timeout during {operation}: {error}")
        except requests.exceptions.ConnectionError as error:
            logging.error(f"Connection error during {operation}: {error}")
        except requests.exceptions.HTTPError as error:
            logging.error(f"HTTP error {error.response.status_code} during {operation}: {error}")
        except json.JSONDecodeError as error:
            logging.error(f"Invalid JSON response during {operation}: {error}")
        except requests.exceptions.RequestException as error:
            logging.error(f"Request failed during {operation}: {error}")

        return None

    def get_token(self, appid, secret, username, passhash):
        """
        Get a token from the API
        :return: access_token
        """
        data = self._make_request(
            url=self.url + f"/account/v1.0/token?appId={appid}&language=en",
            headers={"Content-Type": "application/json"},
            data={"appSecret": secret, "email": username, "password": passhash},
            operation="getting access token"
        )

        if data is None:
            logging.error("Unable to get access token")
            sys.exit(1)

        self.check_response(data)
        logging.debug("Received token")
        return data["access_token"]

    def get_station(self)->int:
        """
        Return station realtime data
        :return: realtime data
        """
        logging.info(f"Requesting station list")

        data = self._make_request(
            url=self.url + "/station/v1.0/list?language=en",
            headers={
                "Content-Type": "application/json",
                "Authorization": "bearer " + self.token,
            },
            data={"page": 1, "size": 50},
            operation="getting station list"
        )

        if data is None:
            return 0

        self.check_response(data)
        logging.info(f"station list: {data}")
        logging.info(f"Found stationList with {len(data['stationList'])} entries")

        if not data["stationList"]:
            return 0

        return int(data["stationList"][0]["id"])

    def get_station_device_list(self):
        """Find the inverter and logger IDs."""
        logging.info(f"Requesting device list")

        data = self._make_request(
            url=self.url + "/station/v1.0/device",
            headers={
                "Content-Type": "application/json",
                "Authorization": "bearer " + self.token,
            },
            data={"stationId": self.station_id},
            operation="getting device list"
        )

        if data is None:
            return

        device_list = data["deviceListItems"]
        logging.debug(f"Found deviceListItems with {len(device_list)} items")

        for device in device_list:
            if device["deviceType"]=="INVERTER":
                logging.info(f"Found inverter with SN {device['deviceSn']} and ID {device['deviceId']}")
                self.inverter_id = int(device["deviceId"])
                self.inverter_sn = device['deviceSn']
            if device["deviceType"]=="COLLECTOR":
                logging.info(f"Found logger with SN {device['deviceId']} and ID {device['deviceId']}")
                self.logger_id = int(device["deviceId"])
                self.logger_sn = device['deviceSn']

    def get_data(self):
        """Get recurring data."""
        self.station_realtime = self.get_station_realtime()

        self.device_current_data_inverter = self.get_device_current_data(
            self.inverter_sn,
            self.inverter_id
        )
        self.device_current_data_logger = self.get_device_current_data(
            self.logger_sn,
            self.logger_id
        )
        

    def get_station_realtime(self):
        """
        Return station realtime data
        :return: realtime data
        """
        data = self._make_request(
            url=self.url + "/station/v1.0/realTime?language=en",
            headers={
                "Content-Type": "application/json",
                "Authorization": "bearer " + self.token,
            },
            data={"stationId": self.station_id},
            operation="getting station realtime data"
        )

        if data is None:
            return None

        self.check_response(data)
        return data

    def get_device_current_data(self, device_sn: str, device_id: int):
        """
        Return device current data
        :return: current data
        """
        payload: dict[str, str | int]
        if device_id == 0:
            payload = {"deviceSn": device_sn}
        else:
            payload = {"deviceSn":device_sn,"deviceId": device_id}

        data = self._make_request(
            url=self.url + "/device/v1.0/currentData?language=en",
            headers={
                "Content-Type": "application/json",
                "Authorization": "bearer " + self.token,
            },
            data=payload,
            operation="getting device current data"
        )

        if data is None:
            return None

        self.check_response(data)
        logging.info(f"current_data:\n{data}")
        return data

    def check_response(self, response: dict) -> None:
        """Check the response for various error codes."""
        if not response:
            logging.warning("Server returned empty response")
            return

        if response.get("success", False):
            # no problems here
            return

        code = int(response.get("code", 0))

        # Code: 2101006. Message: invalid param

        if code==2101009:
            # 'msg': 'appId or api is locked'
            logging.critical("AppId or API is locked")
            # TODO: some sort of timer to retry?
            return

        # this is a problem we have not seen before
        logging.warning(f"Request did not succeed. Code: {code}. Message: {response.get('msg', 'none')}")
        


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
