from datetime import datetime
from urllib.parse import parse_qs, urlsplit


class Author:
    pass


def _first_emoji_shortcut(emoji):
    shortcuts = emoji.get("shortcuts")
    if isinstance(shortcuts, list):
        for shortcut in shortcuts:
            if isinstance(shortcut, str) and shortcut:
                return shortcut
    return ""


def _emoji_accessibility_label(emoji):
    image = emoji.get("image")
    if not isinstance(image, dict):
        return ""
    accessibility = image.get("accessibility")
    if not isinstance(accessibility, dict):
        return ""
    accessibility_data = accessibility.get("accessibilityData")
    if not isinstance(accessibility_data, dict):
        return ""
    label = accessibility_data.get("label")
    return label if isinstance(label, str) else ""


def _emoji_url(emoji):
    image = emoji.get("image")
    if not isinstance(image, dict):
        return ""
    thumbnails = image.get("thumbnails")
    if not isinstance(thumbnails, list):
        return ""
    for thumbnail in thumbnails:
        if isinstance(thumbnail, dict):
            url = thumbnail.get("url")
            if isinstance(url, str) and url:
                return url
    return ""


def _emoji_display_text(emoji):
    emoji_id = emoji.get("emojiId")
    if (isinstance(emoji_id, str) and emoji_id
            and not emoji.get("isCustomEmoji")
            and "/" not in emoji_id):
        return emoji_id
    shortcut = _first_emoji_shortcut(emoji)
    if shortcut:
        return shortcut
    return _emoji_accessibility_label(emoji)


def _emoji_metadata(emoji):
    emoji_id = emoji.get("emojiId")
    if isinstance(emoji_id, str) and emoji_id:
        emoji_id = emoji_id.split("/")[-1]
    else:
        emoji_id = ""
    shortcut = _first_emoji_shortcut(emoji)
    return {
        "id": emoji_id or shortcut,
        "txt": shortcut or _emoji_accessibility_label(emoji),
        "url": _emoji_url(emoji),
    }


def _unwrap_youtube_redirect(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https"):
        return None
    host = (parts.hostname or "").lower()
    if host != "youtube.com" and not host.endswith(".youtube.com"):
        return None
    if parts.path.rstrip("/") != "/redirect":
        return None
    query = parse_qs(parts.query)
    destinations = query.get("q")
    if not destinations:
        return None
    destination = destinations[0].strip()
    if not destination.lower().startswith(("http://", "https://")):
        return None
    return destination


def _navigation_urls(run):
    navigation_endpoint = run.get("navigationEndpoint")
    if not isinstance(navigation_endpoint, dict):
        return []
    candidates = []
    url_endpoint = navigation_endpoint.get("urlEndpoint")
    if isinstance(url_endpoint, dict):
        candidates.append(url_endpoint.get("url"))
    command_metadata = navigation_endpoint.get("commandMetadata")
    if isinstance(command_metadata, dict):
        web_command_metadata = command_metadata.get("webCommandMetadata")
        if isinstance(web_command_metadata, dict):
            candidates.append(web_command_metadata.get("url"))
    urls = []
    for candidate in candidates:
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if candidate.startswith(("http://", "https://")):
                if candidate not in urls:
                    urls.append(candidate)
    for url in list(urls):
        unwrapped = _unwrap_youtube_redirect(url)
        if unwrapped and unwrapped not in urls:
            urls.append(unwrapped)
    return urls


def _restore_full_url(run, text):
    if not isinstance(text, str) or not text:
        return text
    if not text.lower().startswith(("http://", "https://", "www.")):
        return text
    full_urls = _navigation_urls(run)
    if not full_urls:
        return text
    visible = text.rstrip()
    for suffix in ("...", "…"):
        if visible.endswith(suffix):
            visible = visible[:-len(suffix)].rstrip()
            break
    if not visible:
        return text
    visible_for_match = visible
    if visible_for_match.lower().startswith("www."):
        visible_for_match = "https://" + visible_for_match
    if len(visible_for_match) <= len("https://"):
        return text
    for full_url in full_urls:
        if full_url != text and full_url.startswith(visible_for_match):
            return full_url
    return text


class BaseRenderer:
    def setitem(self, item, chat):
        self.item = item
        self.chat = chat
        self.chat.author = Author()

    def settype(self):
        pass

    def get_snippet(self):
        self.chat.id = self.item.get('id')
        timestampUsec = int(self.item.get("timestampUsec", 0))
        self.chat.timestamp = int(timestampUsec / 1000)
        tst = self.item.get("timestampText")
        if tst:
            self.chat.elapsedTime = tst.get("simpleText")
        else:
            self.chat.elapsedTime = ""
        self.chat.datetime = self.get_datetime(timestampUsec)
        self.chat.message, self.chat.messageEx = self.get_message(self.item)
        self.chat.id = self.item.get('id')
        self.chat.amountValue = 0.0
        self.chat.amountString = ""
        self.chat.currency = ""
        self.chat.bgColor = 0

    def get_authordetails(self):
        self.chat.author.badgeUrl = ""
        (self.chat.author.isVerified,
         self.chat.author.isChatOwner,
         self.chat.author.isChatSponsor,
         self.chat.author.isChatModerator) = (
            self.get_badges(self.item)
        )
        self.chat.author.channelId = self.item.get("authorExternalChannelId")
        self.chat.author.channelUrl = "http://www.youtube.com/channel/" + self.chat.author.channelId
        self.chat.author.name = self.item["authorName"]["simpleText"]
        self.chat.author.imageUrl = self.item["authorPhoto"]["thumbnails"][1]["url"]

    def get_message(self, item):
        message = ''
        message_ex = []
        message_data = item.get("message")
        if not isinstance(message_data, dict):
            return message, message_ex
        runs = message_data.get("runs", [])
        if not isinstance(runs, list):
            return message, message_ex
        for r in runs:
            if not isinstance(r, dict):
                continue
            emoji = r.get('emoji')
            if emoji:
                if not isinstance(emoji, dict):
                    continue
                message += _emoji_display_text(emoji)
                message_ex.append(_emoji_metadata(emoji))
            else:
                text = r.get('text', '')
                if not isinstance(text, str):
                    text = ''
                text = _restore_full_url(r, text)
                message += text
                message_ex.append(text)
        return message, message_ex

    def get_badges(self, renderer):
        self.chat.author.type = ''
        isVerified = False
        isChatOwner = False
        isChatSponsor = False
        isChatModerator = False
        badges = renderer.get("authorBadges", {})
        for badge in badges:
            if badge["liveChatAuthorBadgeRenderer"].get("icon"):
                author_type = badge["liveChatAuthorBadgeRenderer"]["icon"]["iconType"]
                self.chat.author.type = author_type
                if author_type == 'VERIFIED':
                    isVerified = True
                if author_type == 'OWNER':
                    isChatOwner = True
                if author_type == 'MODERATOR':
                    isChatModerator = True
            if badge["liveChatAuthorBadgeRenderer"].get("customThumbnail"):
                isChatSponsor = True
                self.chat.author.type = 'MEMBER'
                self.get_badgeurl(badge)
        return isVerified, isChatOwner, isChatSponsor, isChatModerator

    def get_badgeurl(self, badge):
        self.chat.author.badgeUrl = badge["liveChatAuthorBadgeRenderer"]["customThumbnail"]["thumbnails"][0]["url"]

    def get_datetime(self, timestamp):
        dt = datetime.fromtimestamp(timestamp / 1000000)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def get_chatobj(self):
        return self.chat

    def clear(self):
        self.item = None
        self.chat = None
