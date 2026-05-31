"""Plugin registry using metaclass-based auto-registration."""


class RegistryMeta(type):
    _registry = {}

    def __new__(mcs, name, bases, namespace):
        cls = super(RegistryMeta, mcs).__new__(mcs, name, bases, namespace)
        if name != 'Plugin':
            mcs._registry[name] = cls
        return cls


class Plugin(object):
    __metaclass__ = RegistryMeta


class AlphaPlugin(Plugin):
    pass


class BetaPlugin(Plugin):
    pass


def get_plugin(name):
    return RegistryMeta._registry.get(name)
