import httpx
import pytest
from pytchat import util, exceptions
from pytchat.parser.live import Parser
from pytchat.core.pytchat import PytchatCore as Pytchat

VID = "abcdefghijk"
UC = "UC" + "a" * 22


def test_oembed_channel_url(httpx_mock):
    httpx_mock.add_response(json={"author_url": f"https://www.youtube.com/channel/{UC}"})
    assert util._channelid_via_oembed(VID) == UC


def test_oembed_handle_url(httpx_mock):
    httpx_mock.add_response(json={"author_url": "https://www.youtube.com/@someone"})
    httpx_mock.add_response(text=f'..."externalId":"{UC}"...')
    assert util._channelid_via_oembed(VID) == UC


def test_oembed_http_error_returns_none(httpx_mock):
    httpx_mock.add_response(status_code=404)
    assert util._channelid_via_oembed(VID) is None


def test_get_channelid_falls_back_to_scrape(monkeypatch):
    monkeypatch.setattr(util, "_channelid_via_oembed", lambda v: None)
    monkeypatch.setattr(util, "_original_get_channelid", lambda c, v: UC)
    assert util.get_channelid(None, VID) == UC


def test_get_channelid_both_fail(monkeypatch):
    monkeypatch.setattr(util, "_channelid_via_oembed", lambda v: None)

    def boom(c, v):
        raise exceptions.InvalidVideoIdException("x")
    monkeypatch.setattr(util, "_original_get_channelid", boom)
    with pytest.raises(exceptions.InvalidVideoIdException):
        util.get_channelid(None, VID)


def test_parser_raises_nocontents():
    with pytest.raises(exceptions.NoContents):
        Parser(is_replay=False).parse(None)


def test_pytchat_reports_nocontents_not_typeerror(monkeypatch):
    monkeypatch.setattr(util, "get_channelid", lambda c, v: UC)
    monkeypatch.setattr(Pytchat, "_get_livechat_json", lambda *a, **k: {})
    chat = Pytchat(VID, interruptable=False)
    chat.get()
    assert not chat.is_alive()
    with pytest.raises(exceptions.NoContents):
        chat.raise_for_status()
