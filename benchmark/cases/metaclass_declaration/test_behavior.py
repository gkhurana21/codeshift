"""Behavioral oracle for metaclass_declaration."""
from source_py2 import RegistryMeta, Plugin, AlphaPlugin, BetaPlugin, get_plugin


def test_metaclass_applied_to_subclass():
    # In unmigrated Py3, __metaclass__ is a plain attr; type(AlphaPlugin) is type, not RegistryMeta
    assert type(AlphaPlugin) is RegistryMeta


def test_metaclass_applied_to_beta():
    assert type(BetaPlugin) is RegistryMeta


def test_registry_contains_alpha():
    assert get_plugin('AlphaPlugin') is AlphaPlugin


def test_registry_contains_beta():
    assert get_plugin('BetaPlugin') is BetaPlugin


def test_plugin_base_uses_registrymeta():
    # Plugin base itself was created by RegistryMeta even though excluded from registry
    assert type(Plugin) is RegistryMeta
