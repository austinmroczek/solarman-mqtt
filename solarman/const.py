"""Constants"""

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "solarman-mqtt-schema",
    "type": "object",
    "required": [
        "name",
        "url",
        "appid",
        "secret",
        "username",
        "passhash",
        "stationId",
        "inverterId",
        "loggerId",
    ],
    "properties": {
        "name": {
            "type": "string",
        },
        "url": {"type": "string"},
        "appid": {"type": "string", "minLength": 15, "maxLength": 16},
        "secret": {"type": "string", "minLength": 32, "maxLength": 32},
        "username": {"type": "string"},
        "passhash": {"type": "string", "minLength": 64, "maxLength": 64},
        "stationId": {"type": "number", "minimum": 100000, "maximum": 999999999},
        "inverterId": {"type": "string", "minLength": 10},
        "loggerId": {"type": "string", "minLength": 10, "maxLength": 10},
        "meterId": {"type": "string", "minLength": 10},
        "debug": {"type": "boolean", "optional": True},
        "mqtt": {
            "type": "object",
            "properties": {
                "broker": {"type": "string"},
                "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                "topic": {"type": "string"},
                "username": {"type": "string"},
                "password": {"type": "string"},
                "qos": {"type": "integer", "minimum": 1, "maximum": 1},
                "retain": {"type": "boolean"},
            },
        },
    },
}
