import sys
import types


class SICMessage:
    pass


class SICConfMessage(SICMessage):
    pass


class SICRequest(SICMessage):
    pass


class SICStopRequest(SICMessage):
    pass


class AudioMessage(SICMessage):
    def __init__(self, waveform=b"", sample_rate=44100):
        self.waveform = waveform
        self.sample_rate = sample_rate


class TextMessage(SICMessage):
    def __init__(self, text=""):
        self.text = text


class TextRequest(SICRequest):
    def __init__(self, text=""):
        self.text = text


class SICComponent:
    def __init__(self, *args, **kwargs):
        pass


class SICService(SICComponent):
    pass


class SICActuator(SICComponent):
    pass


class SICSensor(SICComponent):
    pass


class SICConnector:
    component_class = SICComponent

    def __init__(self, *args, **kwargs):
        pass


class SICComponentManager:
    def __init__(self, *args, **kwargs):
        pass


class SICRedis:
    def __init__(self, *args, **kwargs):
        pass


def is_sic_instance(obj, cls):
    return isinstance(obj, cls)


def _register_core_stubs():
    if "sic_framework.core" in sys.modules:
        return

    core_mod = types.ModuleType("sic_framework.core")
    utils_mod = types.ModuleType("sic_framework.core.utils")
    utils_mod.is_sic_instance = is_sic_instance
    logging_mod = types.ModuleType("sic_framework.core.sic_logging")

    msg_mod = types.ModuleType("sic_framework.core.message_python2")
    for name, val in [
        ("SICMessage", SICMessage),
        ("SICConfMessage", SICConfMessage),
        ("SICRequest", SICRequest),
        ("SICStopRequest", SICStopRequest),
        ("AudioMessage", AudioMessage),
        ("TextMessage", TextMessage),
        ("TextRequest", TextRequest),
    ]:
        setattr(msg_mod, name, val)

    comp_mod = types.ModuleType("sic_framework.core.component_python2")
    comp_mod.SICComponent = SICComponent

    srv_mod = types.ModuleType("sic_framework.core.service_python2")
    srv_mod.SICService = SICService

    act_mod = types.ModuleType("sic_framework.core.actuator_python2")
    act_mod.SICActuator = SICActuator

    sen_mod = types.ModuleType("sic_framework.core.sensor_python2")
    sen_mod.SICSensor = SICSensor
    sen_mod.SICSensor = SICSensor

    mgr_mod = types.ModuleType("sic_framework.core.component_manager_python2")
    mgr_mod.SICComponentManager = SICComponentManager

    conn_mod = types.ModuleType("sic_framework.core.connector")
    conn_mod.SICConnector = SICConnector

    redis_mod = types.ModuleType("sic_framework.core.sic_redis")
    redis_mod.SICRedis = SICRedis

    core_mod.utils = utils_mod
    core_mod.sic_logging = logging_mod
    core_mod.message_python2 = msg_mod
    core_mod.component_python2 = comp_mod
    core_mod.service_python2 = srv_mod
    core_mod.actuator_python2 = act_mod
    core_mod.sensor_python2 = sen_mod
    core_mod.component_manager_python2 = mgr_mod
    core_mod.connector = conn_mod
    core_mod.sic_redis = redis_mod

    sys.modules["sic_framework.core"] = core_mod
    sys.modules["sic_framework.core.utils"] = utils_mod
    sys.modules["sic_framework.core.sic_logging"] = logging_mod
    sys.modules["sic_framework.core.message_python2"] = msg_mod
    sys.modules["sic_framework.core.component_python2"] = comp_mod
    sys.modules["sic_framework.core.service_python2"] = srv_mod
    sys.modules["sic_framework.core.actuator_python2"] = act_mod
    sys.modules["sic_framework.core.sensor_python2"] = sen_mod
    sys.modules["sic_framework.core.component_manager_python2"] = mgr_mod
    sys.modules["sic_framework.core.connector"] = conn_mod
    sys.modules["sic_framework.core.sic_redis"] = redis_mod


_register_core_stubs()
