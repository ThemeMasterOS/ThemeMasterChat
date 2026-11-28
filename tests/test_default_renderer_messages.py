import pytest

from thememasterchat.processors.default.renderer.textmessage import (
    LiveChatTextMessageRenderer,
)


FULL_URL = "https://www.youtube.com/watch?v=wp6EYn-4kjw"
SHORT_URL = "https://www.youtube.com/watch?v=wp6EY..."
EMOJI_URL = "https://fonts.gstatic.com/s/e/notoemoji/15.1/1f389/72.png"


def render(runs):
    renderer = LiveChatTextMessageRenderer()
    return renderer.get_message({"message": {"runs": runs}})


def native_emoji(**overrides):
    emoji = {
        "emojiId": "🎉",
        "shortcuts": [":party_popper:", ":tada:"],
        "searchTerms": ["party", "popper", "tada"],
        "image": {"thumbnails": [{"url": EMOJI_URL}]},
    }
    emoji.update(overrides)
    return emoji


def url_run(text, full_url):
    return {
        "text": text,
        "navigationEndpoint": {
            "urlEndpoint": {"url": full_url},
            "commandMetadata": {"webCommandMetadata": {"url": full_url}},
        },
    }


def test_plain_text_run():
    assert render([{"text": "hello"}]) == ("hello", ["hello"])


def test_native_emoji_uses_unicode_in_message():
    message, message_ex = render([{"text": "party "}, {"emoji": native_emoji()}])

    assert message == "party 🎉"
    assert message_ex == [
        "party ",
        {
            "id": "🎉",
            "txt": ":party_popper:",
            "url": EMOJI_URL,
        },
    ]


def test_multiple_native_emojis():
    message, message_ex = render([
        {"emoji": native_emoji()},
        {"emoji": native_emoji(emojiId="🚀", shortcuts=[":rocket:"])},
    ])

    assert message == "🎉🚀"
    assert [item["txt"] for item in message_ex] == [":party_popper:", ":rocket:"]


def test_mixed_text_and_emojis():
    message, _ = render([
        {"text": "hello "},
        {"emoji": native_emoji()},
        {"text": " world"},
        {"emoji": native_emoji(emojiId="🚀", shortcuts=[":rocket:"])},
    ])

    assert message == "hello 🎉 world🚀"


def test_custom_emoji_keeps_shortcut():
    emoji = native_emoji(
        emojiId="UCoSrY_IQQVpmIRZ9Xf-y93g/1wyJX8HwDMu68wTNxJO4DQ",
        shortcuts=[":_GuraAA:"],
        isCustomEmoji=True,
    )

    message, message_ex = render([{"emoji": emoji}])

    assert message == ":_GuraAA:"
    assert message_ex[0]["id"] == "1wyJX8HwDMu68wTNxJO4DQ"
    assert message_ex[0]["txt"] == ":_GuraAA:"


def test_missing_emoji_id_falls_back_to_shortcut():
    message, message_ex = render([
        {"emoji": {"shortcuts": [":party:"], "image": {"thumbnails": [{"url": EMOJI_URL}]}}}
    ])

    assert message == ":party:"
    assert message_ex[0]["id"] == ":party:"
    assert message_ex[0]["txt"] == ":party:"


def test_missing_emoji_shortcut_still_uses_unicode():
    message, message_ex = render([{"emoji": {"emojiId": "🎉", "image": {}}}])

    assert message == "🎉"
    assert message_ex[0]["id"] == "🎉"
    assert message_ex[0]["txt"] == ""
    assert message_ex[0]["url"] == ""


def test_emoji_without_image_does_not_raise():
    message, message_ex = render([
        {"emoji": {"emojiId": "🎉", "shortcuts": [":party_popper:"]}}
    ])

    assert message == "🎉"
    assert message_ex[0]["url"] == ""


def test_malformed_emoji_data_is_skipped():
    assert render([{"emoji": "not-a-dict"}]) == ("", [])
    assert render([{"emoji": {}, "text": "fallback"}]) == ("fallback", ["fallback"])


def test_shortened_url_restored_from_url_endpoint():
    message, message_ex = render([
        {"text": "watch "},
        url_run(SHORT_URL, FULL_URL),
    ])

    assert message == "watch " + FULL_URL
    assert message_ex == ["watch ", FULL_URL]


def test_shortened_url_restored_from_command_metadata():
    run = {
        "text": SHORT_URL,
        "navigationEndpoint": {
            "commandMetadata": {"webCommandMetadata": {"url": FULL_URL}}
        },
    }

    assert render([run]) == (FULL_URL, [FULL_URL])


def test_shortened_url_uses_matching_command_metadata_candidate():
    run = {
        "text": SHORT_URL,
        "navigationEndpoint": {
            "urlEndpoint": {"url": "https://www.youtube.com/redirect?q=unrelated"},
            "commandMetadata": {"webCommandMetadata": {"url": FULL_URL}},
        },
    }

    assert render([run]) == (FULL_URL, [FULL_URL])


def test_direct_navigation_url_takes_precedence_over_redirect_destination():
    run = {
        "text": "https://example.com/some...",
        "navigationEndpoint": {
            "urlEndpoint": {
                "url": "https://www.youtube.com/redirect?q=https%3A%2F%2Fexample.com%2Fsome%2Flong%2Furl"
            },
            "commandMetadata": {
                "webCommandMetadata": {"url": "https://example.com/some/other"}
            },
        },
    }

    assert render([run]) == ("https://example.com/some/other", ["https://example.com/some/other"])


def test_shortened_url_without_metadata_is_preserved():
    assert render([{"text": SHORT_URL}]) == (SHORT_URL, [SHORT_URL])


def test_non_matching_navigation_metadata_is_preserved():
    run = {
        "text": SHORT_URL,
        "navigationEndpoint": {"urlEndpoint": {"url": "https://example.com/other"}},
    }

    assert render([run]) == (SHORT_URL, [SHORT_URL])


def test_redirect_navigation_metadata_is_unwrapped():
    redirect_url = (
        "https://www.youtube.com/redirect?event=live_chat"
        "&q=https%3A%2F%2Fexample.com%2Fsome%2Flong%2Furl"
    )
    run = {
        "text": "https://example.com/some...",
        "navigationEndpoint": {"urlEndpoint": {"url": redirect_url}},
    }

    assert render([run]) == (
        "https://example.com/some/long/url",
        ["https://example.com/some/long/url"],
    )


def test_redirect_q_parameter_is_percent_decoded():
    destination = "https://test.com/hdufhfasasfueeeetstestetdggddh"
    redirect_url = (
        "https://www.youtube.com/redirect?event=live_chat"
        "&redir_token=abc123&q=https%3A%2F%2Ftest.com%2Fhdufhfasasfueeeetstestetdggddh"
    )
    run = {
        "text": "https://test.com/hdufhfasas...",
        "navigationEndpoint": {"urlEndpoint": {"url": redirect_url}},
    }

    assert render([run]) == (destination, [destination])


def test_redirect_destination_with_encoded_query_is_decoded():
    destination = "https://example.com/search?q=a%26b&lang=en"
    redirect_url = (
        "https://www.youtube.com/redirect?q="
        "https%3A%2F%2Fexample.com%2Fsearch%3Fq%3Da%2526b%26lang%3Den"
    )
    run = {
        "text": "https://example.com/search?q=a...",
        "navigationEndpoint": {"urlEndpoint": {"url": redirect_url}},
    }

    assert render([run]) == (destination, [destination])


def test_redirect_without_destination_is_preserved():
    run = {
        "text": "https://example.com/some...",
        "navigationEndpoint": {
            "urlEndpoint": {"url": "https://www.youtube.com/redirect?event=live_chat"}
        },
    }

    assert render([run]) == ("https://example.com/some...", ["https://example.com/some..."])


def test_redirect_with_non_url_destination_is_preserved():
    run = {
        "text": "https://example.com/some...",
        "navigationEndpoint": {
            "urlEndpoint": {"url": "https://www.youtube.com/redirect?q=not-a-url"}
        },
    }

    assert render([run]) == ("https://example.com/some...", ["https://example.com/some..."])


def test_non_youtube_redirect_is_not_unwrapped():
    redirect_url = (
        "https://example.com/redirect?q=https%3A%2F%2Fexample.com%2Fsome%2Flong%2Furl"
    )
    run = {
        "text": "https://example.com/some...",
        "navigationEndpoint": {"urlEndpoint": {"url": redirect_url}},
    }

    assert render([run]) == ("https://example.com/some...", ["https://example.com/some..."])


def test_malformed_redirect_url_does_not_raise():
    run = {
        "text": "https://example.com/some...",
        "navigationEndpoint": {"urlEndpoint": {"url": "https://www.youtube.com/redirect?q=%"}},
    }

    assert render([run]) == ("https://example.com/some...", ["https://example.com/some..."])


def test_normal_linked_text_is_preserved():
    run = {
        "text": "click here",
        "navigationEndpoint": {"urlEndpoint": {"url": "https://example.com"}},
    }

    assert render([run]) == ("click here", ["click here"])


def test_full_url_is_unchanged():
    assert render([url_run(FULL_URL, FULL_URL)]) == (FULL_URL, [FULL_URL])


def test_www_url_is_restored():
    run = {
        "text": "www.youtube.com/watch?v=wp6EY...",
        "navigationEndpoint": {"urlEndpoint": {"url": FULL_URL}},
    }

    assert render([run]) == (FULL_URL, [FULL_URL])


def test_multiple_urls_are_restored():
    second_full = "https://example.com/a/very/long/path"
    second_short = "https://example.com/a/very..."
    message, message_ex = render([
        url_run(SHORT_URL, FULL_URL),
        {"text": " and "},
        url_run(second_short, second_full),
    ])

    assert message == FULL_URL + " and " + second_full
    assert message_ex == [FULL_URL, " and ", second_full]


@pytest.mark.parametrize("navigation_endpoint", [
    None,
    "not-a-dict",
    {},
    {"urlEndpoint": {}},
    {"urlEndpoint": {"url": "not-a-url"}},
    {"urlEndpoint": {"url": 123}},
    {"commandMetadata": {"webCommandMetadata": {"url": None}}},
])
def test_malformed_navigation_metadata_is_preserved(navigation_endpoint):
    run = {"text": SHORT_URL, "navigationEndpoint": navigation_endpoint}

    assert render([run]) == (SHORT_URL, [SHORT_URL])


def test_mixed_runs_preserve_order():
    message, message_ex = render([
        {"text": "look "},
        {"emoji": native_emoji()},
        {"text": " "},
        url_run(SHORT_URL, FULL_URL),
        {"text": " now"},
    ])

    assert message == "look 🎉 " + FULL_URL + " now"
    assert message_ex == [
        "look ",
        {"id": "🎉", "txt": ":party_popper:", "url": EMOJI_URL},
        " ",
        FULL_URL,
        " now",
    ]
