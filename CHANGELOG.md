# Changelog

All notable changes to ThemeMasterChat are documented here.

## [0.1.1.0] - 2026-11-26

This release renames the Python import package to `thememasterchat` and improves how chat messages are rendered: native emojis now appear as real Unicode emojis, and shortened URLs are expanded back to their full form when YouTube provides reliable navigation metadata.

### ⚠️ Breaking change: import name

The Python import package is now **`thememasterchat`** (previously `pytchat`).

```python
# Before
import pytchat
chat = pytchat.create(video_id="VIDEO_ID")

# After
import thememasterchat
chat = thememasterchat.create(video_id="VIDEO_ID")
```

The distribution name is still `thememasterchat`, so upgrading replaces the old `pytchat/` import directory:

```bash
pip install -U thememasterchat
```

If the original `pytchat` / `pytchat-ng` packages are installed, `import pytchat` will load those packages, not ThemeMasterChat.

#### Compatibility alias

If you don't want to rename existing `pytchat` references, use a local import alias:

```python
import thememasterchat as pytchat

chat = pytchat.create(video_id="VIDEO_ID")
```

This is only a Python import alias; it does not install or re-export the original `pytchat` package.

### Added

- Native emoji rendering: native emojis are rendered as Unicode emojis in `message` using the emoji's `emojiId`.
- Full URL restoration: shortened URLs shown in chat (e.g. `https://www.youtube.com/watch?v=wp6EY...`) are restored to the full URL when navigation metadata reliably matches the visible text.
- Regression tests for emoji rendering and URL restoration.
- Package import/version and internal-import tests.

### Changed

- Renamed the Python import package from `pytchat` to `thememasterchat`.
- Version bumped to `0.1.1.0`.
- `messageEx[].txt` intentionally keeps shortcut text for backward compatibility.
- Custom emojis and path-like/malformed emoji IDs fall back to shortcut text or the accessibility label.
- URL restoration checks `navigationEndpoint.urlEndpoint.url` first, then `navigationEndpoint.commandMetadata.webCommandMetadata.url`.
- URL restoration handles both `...` and `…` truncation.
- URL restoration applies to both `message` and `messageEx` string runs.
- Renderer changes are limited to the **default renderer**; other processors and public APIs are unchanged.
- Updated all tests to import `thememasterchat`.

### Fixed

- Fixed the internal import in the superchat calculator (`from ..chat_processor import ChatProcessor`) so it works correctly after the package rename.

### Compatibility

- `PytchatCore` class name unchanged.
- `thememasterchat/core/pytchat.py` module path unchanged.
- Existing public exports (`create`, processors, archivers, exceptions, etc.) unchanged.
- YouTube redirect URLs are **not** unwrapped.

### Documentation

- Added a breaking-change warning and upgrade guidance to the README.
- Updated all examples to `import thememasterchat`.
- Added a compatibility-alias section for existing `pytchat` code.
- Documented the new emoji and URL behavior in the default processor field table.

### Requirements

- Python >= 3.8
- `httpx[http2]`
