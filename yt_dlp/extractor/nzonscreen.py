from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    remove_end,
    smuggle_url,
    strip_or_none,
    traverse_obj,
    unsmuggle_url,
    url_or_none,
)


class NZOnScreenBaseIE(InfoExtractor):
    _HTTP_HEADERS = {
        'Referer': 'https://www.nzonscreen.com/',
        'Origin': 'https://www.nzonscreen.com/',
    }

    def _download_video_data(self, display_id, video_id):
        return self._download_json(
            f'https://www.nzonscreen.com/html5/video_data/{display_id}',
            video_id, note='Downloading video data', fatal=False)

    def _extract_alt_title(self, webpage):
        return strip_or_none(remove_end(
            self._html_extract_title(webpage, default=None) or self._og_search_title(webpage, default=None),
            ' | NZ On Screen'))

    @staticmethod
    def _find_video(video_data, uuid):
        if not isinstance(video_data, list):
            return None
        return next((video for video in video_data if video.get('uuid') == uuid), None)

    @staticmethod
    def _extract_formats(playlist):
        return [{
            'url': format_url,
            'format_id': format_id,
            'ext': 'mp4',
            'quality': quality,
            'height': int_or_none(playlist.get('height')) if format_id == 'hi' else None,
            'width': int_or_none(playlist.get('width')) if format_id == 'hi' else None,
            'filesize_approx': float_or_none(traverse_obj(playlist, ('h264', f'{format_id}_res_mb')), invscale=1024**2),
        } for quality, (format_id, format_url) in enumerate((traverse_obj(
            playlist, ('h264', {'lo': 'lo_res', 'hi': 'hi_res'}), expected_type=url_or_none) or {}).items())]

    def _extract_video_info(self, playlist, display_id, *, alt_title=None):
        return {
            'id': playlist.get('uuid') or display_id,
            'display_id': display_id,
            'title': strip_or_none(playlist.get('label')),
            'description': strip_or_none(playlist.get('description')),
            'alt_title': alt_title,
            'thumbnail': traverse_obj(playlist, ('thumbnail', 'path')),
            'duration': float_or_none(playlist.get('duration')),
            'formats': self._extract_formats(playlist),
            'http_headers': self._HTTP_HEADERS,
        }


class NZOnScreenVideoIE(NZOnScreenBaseIE):
    _VALID_URL = r'nzonscreen:video:(?P<id>[^:]+):(?P<uuid>[a-f0-9]+)'

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        uuid = mobj.group('uuid')

        playlist = self._find_video(self._download_video_data(display_id, uuid), uuid)
        if not playlist:
            playlist = traverse_obj(smuggled_data, ('playlist', {dict}))
        if not playlist:
            raise ExtractorError(f'Video {uuid} not found in playlist')
        return self._extract_video_info(playlist, display_id, alt_title=smuggled_data.get('alt_title'))


class NZOnScreenIE(NZOnScreenBaseIE):
    _VALID_URL = r'https?://www\.nzonscreen\.com/title/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.nzonscreen.com/title/shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
        'info_dict': {
            'id': '726ed6585c6bfb30',
            'ext': 'mp4',
            'format_id': 'hi',
            'display_id': 'shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
            'title': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'description': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'alt_title': 'Shoop Shoop Diddy Wop Cumma Cumma Wang Dang | Music Video',
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 158,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/shes-a-mod-1964?collection=best-of-the-60s',
        'info_dict': {
            'id': '3dbe709ff03c36f1',
            'ext': 'mp4',
            'format_id': 'hi',
            'display_id': 'shes-a-mod-1964',
            'title': 'Ray Columbus - \'She\'s A Mod\'',
            'description': 'Ray Columbus - \'She\'s A Mod\'',
            'alt_title': 'She\'s a Mod | Music Video',
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
            'duration': 130,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nzonscreen.com/title/puha-and-pakeha-1968/overview',
        'info_dict': {
            'id': 'f86342544385ad8a',
            'ext': 'mp4',
            'format_id': 'hi',
            'display_id': 'puha-and-pakeha-1968',
            'title': 'Looking At New Zealand - Puha and Pakeha',
            'alt_title': 'Looking at New Zealand - \'Pūhā and Pākehā\' | Television',
            'description': 'An excerpt from this television programme.',
            'duration': 212,
            'thumbnail': r're:https://www\.nzonscreen\.com/content/images/.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Multiple videos (trailer + full length)
        'url': 'https://www.nzonscreen.com/title/the-deadly-ponies-gang-2013',
        'info_dict': {
            'id': 'the-deadly-ponies-gang-2013',
            'title': 'The Deadly Ponies Gang | Film',
        },
        'playlist_count': 2,
        'params': {'skip_download': 'm3u8'},
    }]

    def _video_result(self, display_id, uuid, *, alt_title=None, playlist=None, **kwargs):
        smuggled_data = {}
        if alt_title:
            smuggled_data['alt_title'] = alt_title
        if playlist:
            smuggled_data['playlist'] = playlist
        return self.url_result(
            smuggle_url(f'nzonscreen:video:{display_id}:{uuid}', smuggled_data),
            ie=NZOnScreenVideoIE, video_id=uuid, url_transparent=True, **kwargs)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        alt_title = self._extract_alt_title(webpage)

        video_data = self._download_video_data(video_id, video_id)
        if isinstance(video_data, list):
            if len(video_data) > 1:
                entries = [self._video_result(
                    video_id, uuid, alt_title=alt_title,
                    title=strip_or_none(video.get('label')),
                    description=strip_or_none(video.get('description')),
                    thumbnail=traverse_obj(video, ('thumbnail', 'path')),
                    duration=float_or_none(video.get('duration')))
                    for video in video_data if (uuid := video.get('uuid'))]
                if entries:
                    return self.playlist_result(entries, video_id, alt_title)
            elif len(video_data) == 1:
                playlist = video_data[0]
                if uuid := playlist.get('uuid'):
                    return self._video_result(video_id, uuid, alt_title=alt_title)
                return self._extract_video_info(playlist, video_id, alt_title=alt_title)

        playlist = self._parse_json(self._html_search_regex(
            r'data-video-config=\'([^\']+)\'', webpage, 'media data'), video_id)
        if uuid := playlist.get('uuid'):
            return self._video_result(video_id, uuid, alt_title=alt_title, playlist=playlist)
        return self._extract_video_info(playlist, video_id, alt_title=alt_title)
