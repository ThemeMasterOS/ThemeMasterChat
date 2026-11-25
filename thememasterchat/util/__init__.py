import datetime
import os
import re
from typing import Optional
from urllib.parse import quote
import httpx
from .. import config
from .. exceptions import InvalidVideoIdException

PATTERN = re.compile(r"(.*)\(([0-9]+)\)$")

PATTERN_YTURL = re.compile(r"((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)")

PATTERN_CHANNEL = re.compile(r"\\\"channelId\\\":\\\"(.{24})\\\"")

PATTERN_M_CHANNEL = re.compile(r"\"channelId\":\"(.{24})\"")

PATTERN_OEMBED_CHANNEL = re.compile(r"/channel/(UC[0-9A-Za-z_-]{22})")

PATTERN_EXTERNAL_ID = re.compile(r'"externalId":"(UC[0-9A-Za-z_-]{22})"')

YT_VIDEO_ID_LENGTH = 11

CLIENT_VERSION = ''.join(("2.", (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y%m%d"), ".01.00"))

UA = config.headers["user-agent"]

def _channelid_via_oembed(video_id: str) -> Optional[str]:
    """Try to resolve a channel ID using YouTube's oEmbed endpoint.

    Returns None on any network/parse failure so the caller can fall back
    to HTML scraping. Programming errors (NameError etc.) are NOT swallowed.
    """
    oembed_url = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={quote(video_id)}&format=json"
    )
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(oembed_url)
            if resp.status_code != 200:
                return None

            author_url = resp.json().get("author_url", "")
            if not author_url:
                return None

            # author_url is usually .../channel/UCxxxxxxxx
            match = PATTERN_OEMBED_CHANNEL.search(author_url)
            if match:
                return match.group(1)

            # Newer @handle-style author_url: resolve via the about page.
            if "/@" in author_url:
                about_resp = client.get(author_url + "/about", follow_redirects=True)
                match2 = PATTERN_EXTERNAL_ID.search(about_resp.text)
                if match2:
                    return match2.group(1)
    except (httpx.HTTPError, ValueError, KeyError, AttributeError):
        return None

    return None


def save(data, filename, extention) -> str:
    save_filename = filename + "_" + \
        (datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')) + extention
    with open(save_filename, mode='w', encoding='utf-8') as f:
        f.writelines(data)
    return save_filename


def checkpath(filepath):
    splitter = os.path.splitext(os.path.basename(filepath))
    body = splitter[0]
    extention = splitter[1]
    newpath = filepath
    counter = 1
    while os.path.exists(newpath):
        match = re.search(PATTERN, body)
        if match:
            counter = int(match[2]) + 1
            num_with_bracket = f'({str(counter)})'
            body = f'{match[1]}{num_with_bracket}'
        else:
            body = f'{body}({str(counter)})'
        newpath = os.path.join(os.path.dirname(filepath), body + extention)
    return newpath


def get_param(continuation, replay=False, offsetms: int = 0, dat=''):
    if offsetms < 0:
        offsetms = 0
    ret = {
        "context": {
            "client": {
                "visitorData": dat,
                "userAgent": UA,
                "clientName": "WEB",
                "clientVersion": CLIENT_VERSION,
            },

        },
        "continuation": continuation,
    }
    if replay:
        ret.setdefault("currentPlayerState", {
                       "playerOffsetMs": str(int(offsetms))})
    return ret


def extract_video_id(url_or_id: str) -> str:
    ret = ''
    if '[' in url_or_id:
        url_or_id = url_or_id.replace('[', '').replace(']', '')

    if type(url_or_id) != str:
        raise TypeError(f"{url_or_id}: URL or VideoID must be str, but {type(url_or_id)} is passed.")
    if len(url_or_id) == YT_VIDEO_ID_LENGTH:
        return url_or_id
    match = re.search(PATTERN_YTURL, url_or_id)
    if match is None:
        raise InvalidVideoIdException(f"Invalid video id: {url_or_id}")
    try:
        ret = match.group(4)
    except IndexError:
        raise InvalidVideoIdException(f"Invalid video id: {url_or_id}")

    if ret is None or len(ret) != YT_VIDEO_ID_LENGTH:
        raise InvalidVideoIdException(f"Invalid video id: {url_or_id}")
    return ret


def _original_get_channelid(client, video_id):
    """Original pytchat lookup: scrape the embed page, then the mobile page."""
    resp = client.get("https://www.youtube.com/embed/{}".format(quote(video_id)), headers=config.headers)
    match = re.search(PATTERN_CHANNEL, resp.text)
    try:
        if match is None:
            raise IndexError
        ret = match.group(1)
    except IndexError:
        ret = get_channelid_2nd(client, video_id)
    return ret


def get_channelid(client, video_id):
    """Resolve a channel ID: oEmbed first, then the original HTML scraping."""
    channel_id = _channelid_via_oembed(video_id)
    if channel_id:
        return channel_id

    try:
        return _original_get_channelid(client, video_id)
    except InvalidVideoIdException as e:
        raise InvalidVideoIdException(
            f"Cannot find channel id for video id:{video_id}. "
            "Both oEmbed and HTML-scrape lookups failed."
        ) from e


def get_channelid_2nd(client, video_id):
    resp = client.get("https://m.youtube.com/watch?v={}".format(quote(video_id)), headers=config.m_headers)  
    
    match = re.search(PATTERN_M_CHANNEL, resp.text)
    if match is None:
        raise InvalidVideoIdException(f"Cannot find channel id for video id:{video_id}. This video id seems to be invalid.")
    try:
        ret = match.group(1)
    except IndexError:
        raise InvalidVideoIdException(f"Invalid video id: {video_id}")
    return ret


async def get_channelid_async(client, video_id):
    resp = await client.get("https://www.youtube.com/embed/{}".format(quote(video_id)), headers=config.headers)  
    match = re.search(PATTERN_CHANNEL, resp.text)
    try:
        if match is None:
            raise IndexError
        ret = match.group(1)
    except IndexError:
        ret = await get_channelid_async_2nd(client, video_id)
    return ret

async def get_channelid_async_2nd(client, video_id):
    resp = await client.get("https://m.youtube.com/watch?v={}".format(quote(video_id)), headers=config.m_headers)  
    match = re.search(PATTERN_M_CHANNEL, resp.text)
    if match is None:
        raise InvalidVideoIdException(f"Cannot find channel id for video id:{video_id}. This video id seems to be invalid.")
    try:
        ret = match.group(1)
    except IndexError:
        raise InvalidVideoIdException(f"Invalid video id: {video_id}")
    return ret
