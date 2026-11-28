import thememasterchat

from thememasterchat.processors.chat_processor import ChatProcessor
from thememasterchat.processors.superchat.calculator import SuperchatCalculator


def test_renamed_package_public_api():
    assert thememasterchat.__version__ == "0.1.1.1"
    assert callable(thememasterchat.create)


def test_renamed_package_internal_imports():
    assert issubclass(SuperchatCalculator, ChatProcessor)
