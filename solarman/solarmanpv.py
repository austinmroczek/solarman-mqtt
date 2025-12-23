"""
SolarmanPV - Collect PV data from the SolarmanPV API and send Power+Energy data (W+kWh) to MQTT
"""

import json
import logging
import sys
import time
from hashlib import sha256

from jsonschema import validate
from jsonschema.exceptions import SchemaError, ValidationError

from .api import ConstructData, SolarmanApi
from .const import SCHEMA
from .mqtt import Mqtt

logging.basicConfig(level=logging.INFO)


class SolarmanPV:
    """
    SolarmanPV data collection and MQTT publishing
    """

    def __init__(self, file):
        self.config = self.load_config(file)

    def load_config(self, file):
        """
        Load configuration
        :return:
        """
        with open(file, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        if not isinstance(config, list):
            config = [config]

        return config

    def validate_config(self, config):
        """
        Validate config file
        :param file: Config file
        :return:
        """
        config = self.load_config(config)
        for conf in config:
            print(
                f"## CONFIG INSTANCE NAME: {conf['name']} [{config.index(conf) + 1}/{len(config)}]"
            )
            try:
                validate(instance=self.config, schema=SCHEMA)
            except ValidationError as err:
                logging.critial(err.message)
                sys.exit(1)
            except SchemaError as err:
                logging.critial(err.message)
                sys.exit(1)


    def single_run(self, config):
        """
        Output current watts and kilowatts
        :return:
        """
        pvdata = SolarmanApi(config)

        station_data = pvdata.station_realtime
        inverter_data = pvdata.device_current_data_inverter
        logging.info(f"inverter_data: {inverter_data}")
        logger_data = pvdata.device_current_data_logger
        logging.info(f"logger_data: {logger_data}")

        inverter_data_list = ConstructData(inverter_data).device_current_data
        logger_data_list = ConstructData(logger_data).device_current_data

        if config.get("debug", False):
            logging.info(json.dumps("STATION DATA"))
            logging.info(json.dumps(station_data, indent=4, sort_keys=True))
            logging.info(json.dumps("INVERTER DATA"))
            logging.info(json.dumps(inverter_data, indent=4, sort_keys=True))
            logging.info(json.dumps("INVERTER DATA LIST"))
            logging.info(json.dumps(inverter_data_list, indent=4, sort_keys=True))
            logging.info(json.dumps("LOGGER DATA"))
            logging.info(json.dumps(logger_data, indent=4, sort_keys=True))
            logging.info(json.dumps("LOGGER DATA LIST"))
            logging.info(json.dumps(logger_data_list, indent=4, sort_keys=True))

        _t = time.strftime("%Y-%m-%d %H:%M:%S")

        mqtt = Mqtt(config["mqtt"])

        if station_data:
            if not station_data.get("success", False):
                logging.warning(f"{_t} station_data request failed.  Response: {station_data}")
            else:
                logging.info(f"{_t} station_data updated")
                for i in station_data:
                    mqtt.publish("/station/" + i, station_data[i])


        if inverter_data:
            if not inverter_data.get("success", False):
                logging.warning(f"inverter_data request failed.  Response: {inverter_data}")
            else:
                logging.info(f"{_t} inverter_data updated")
                for i in inverter_data:
                    mqtt.publish("/inverter/" + i, inverter_data[i])
                mqtt.publish("/inverter/attributes",json.dumps(inverter_data_list))

        if logger_data:
            if not logger_data.get("success", False):
                logging.warning(f"logger_data request failed.  Response: {logger_data}")
            else:
                logging.info(f"{_t} logger_data updated")
                for i in logger_data:
                    mqtt.publish("/logger/" + i, logger_data[i])
                mqtt.publish("/logger/attributes",json.dumps(logger_data_list))


    def single_run_loop(self):
        """
        Perform single runs for all config instances
        """
        for conf in self.config:
            self.single_run(conf)

    def daemon(self, interval):
        """
        Run as a daemon process
        :param file: Config file
        :param interval: Run interval in seconds
        :return:
        """
        interval = int(interval)
        logging.info(
            "Starting daemonized with a %s seconds run interval", str(interval)
        )
        while True:
            try:
                self.single_run_loop()
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("Exiting on keyboard interrupt")
                sys.exit(0)
            except Exception as error:  # pylint: disable=broad-except
                logging.error("Error on start: %s", str(error))
                sys.exit(1)

    def create_passhash(self, password):
        """
        Create passhash from password
        :param password: Password
        :return:
        """
        passhash = sha256(password.encode()).hexdigest()
        print(passhash)
        return passhash
