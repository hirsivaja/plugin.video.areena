# -*- coding: utf-8 -*-
# Module: default
# Author: Samuli Lappi
# Created on: 2015-12-05

import sys
import urllib
import json
import base64
from urlparse import parse_qsl
import datetime
import time
import re
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

_addonid = 'plugin.video.areena'
_addon = xbmcaddon.Addon(id=_addonid)

_yle_time_format = '%Y-%m-%dT%H:%M:%S'
_unplayableCategories = ["5-162", "5-164", "5-226", "5-228"]

_tv_services = ['yle-tv1', 'yle-tv2', 'yle-teema-fem', 'yle-areena', 'tv-finland']

_yle_tv1_live_url = 'http://yletv-lh.akamaihd.net/i/yletv1hls_1@103188/master.m3u8'
_yle_tv2_live_url = 'http://yletv-lh.akamaihd.net/i/yletv2hls_1@103189/master.m3u8'
_image_cdn_url = 'http://images.cdn.yle.fi/image/upload'
_image_transformation = 'w_240,h_240,c_fit'


def log(txt, log_level=xbmc.LOGDEBUG):
    """
    Log something to the kodi.log file
    :param txt: Text to write to the log
    :param log_level: Severity of the log text
    :return: None
    """
    if (_addon.getSetting("debug") == "true") or (log_level != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            try:
                txt = txt.decode("utf-8")
            except UnicodeDecodeError:
                xbmc.log('Could not decode to Unicode: {0}'.format(txt), level=xbmc.LOGWARNING)
                return
        message = u'%s: %s' % (_addonid, txt)
        xbmc.log(msg=message.encode("utf-8"), level=log_level)


def get_areena_api_json_data(folder_name, json_name, parameters):
    """
    Return the data portion of the json response from the Yle API
    :param folder_name: folder part of the URL
    :param json_name: name of the JSON file in the URL
    :param parameters: get parameters for the url
    :return: data from the JSON response
    """
    url = get_areena_api_url(folder_name, json_name, parameters)
    response = get_url_response(url)
    log(response)
    if response is None or response == '':
        raise ValueError('Request "{0}" returned an empty response.'.format(url))
    data = json.loads(response.read())
    log(data)
    return data['data']


def get_areena_api_url(folder_name, item_name, parameters):
    parameters.append('app_id=' + get_app_id())
    parameters.append('app_key=' + get_app_key())
    protocol = 'https'
    if _addon.getSetting("https") == "false":
        protocol = 'http'
    url = '{0}://external.api.yle.fi/v1/{1}/{2}?{3}'.format(protocol, folder_name, item_name, '&'.join(parameters))
    log(url)
    return url


def get_categories():
    """
    Get a list of all the categories.
    :return: list of categories in JSON
    """
    return get_areena_api_json_data('programs', 'categories.json', [])


def get_items(offset, category=None, query=None, limit=None, series=None):
    """
    Get the list of items.
    :param offset: offset for streams to retrieve
    :param category: possible category id
    :param query: possible search query
    :param limit: possible search limit
    :param series: possible serie to list
    :return: json data of the items
    """
    parameters = []
    if category:
        parameters.append('category={0}'.format(category))
    if query:
        parameters.append('q={0}'.format(query))
    if limit:
        parameters.append('limit={0}'.format(limit))
    if series:
        parameters.append('series=' + series)
    if _addon.getSetting("showClips") == "false":
        parameters.append('type=program')
    if _addon.getSetting("inFinland") == "false":
        parameters.append('region=world')
    if _addon.getSetting("showUnplayable") == "false":
        parameters.append('contentprotection=22-0,22-1')
    parameters.append('availability=ondemand')
    parameters.append('order=' + get_sort_method())
    parameters.append('offset=' + str(offset))
    return get_areena_api_json_data('programs', 'items.json', parameters)


def get_item(program_id):
    """
    Get the item data
    :param program_id: Unique ID of the item
    :return: json data of the item
    """
    return get_areena_api_json_data('programs/items', '{0}.json'.format(program_id), [])


def get_playout(program_id, media_id, protocol):
    parameters = ['program_id=' + program_id, 'media_id=' + media_id, 'protocol=' + protocol]
    return get_areena_api_json_data('media', 'playouts.json', parameters)


def get_report_url(program_id, media_id):
    parameters = ['program_id=' + program_id, 'media_id=' + media_id]
    return get_areena_api_url('tracking', 'streamstart', parameters)


def list_categories(base_category):
    """
    Create the list of the categories in the Kodi interface.
    :param base_category: the parent category to require from all categories
    :return: None
    """
    listing = list_sub_categories(base_category)
    # Add our listing to Kodi.
    # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
    # instead of adding one by ove via addDirectoryItem.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_sub_categories(base_category):
    # Get the categories
    categories = get_categories()
    # Create a list for our items.
    listing = []
    # Iterate through categories
    for category in categories:
        unplayable = False
        if 'broader' not in category:
            continue
        if 'id' not in category['broader']:
            continue
        if category['id'] in _unplayableCategories or category['broader']['id'] in _unplayableCategories:
            if _addon.getSetting('showUnplayable') == 'true':
                unplayable = True
            else:
                continue
        if category['broader']['id'] == base_category:
            # Create a list item with a text label and a thumbnail image.
            for language_code in get_language_codes():
                if language_code in category['title']:
                    if unplayable:
                        category_title = '[COLOR {0}]{1}[/COLOR]'.format(
                            get_color('unplayableColor'), category['title'][language_code].encode('utf-8'))
                    else:
                        category_title = '[COLOR {0}]{1}[/COLOR]'.format(
                            get_color('menuItemColor'), category['title'][language_code].encode('utf-8'))
                    break
            list_item = xbmcgui.ListItem(label=category_title)
            # Set additional info for the list item.
            list_item.setInfo('video', {'title': category_title, 'genre': category['type']})
            # Create a URL for the plugin recursive callback.
            url = '{0}?action=listing&category={1}'.format(_url, category['id'])
            # is_folder = True means that this item opens a sub-list of lower level items.
            is_folder = True
            # Add our item to the listing as a 3-element tuple.
            listing.append((url, list_item, is_folder))
    return listing


def list_series(series_id, offset):
    series = get_items(offset, series=series_id)
    series_url = '{0}?action=series&series_id={1}&offset={2}'.format(_url, series_id, offset + 25)
    list_streams([], series, series_url)


def get_image_url_for_series(series_id):
    series_items = get_items(0, series=series_id, limit=1)
    if series_items:
        series_item = series_items[0]
        if 'partOfSeries' in series_item:
            if 'available' in series_item['partOfSeries']['image']:
                if series_item['partOfSeries']['image']['available']:
                    image_url = '{0}/{1}/{2}.{3}'.format(
                        _image_cdn_url, _image_transformation, series_item['partOfSeries']['image']['id'], 'png')
                    return image_url
    else:
        return 'NO_ITEMS'
    log('Could not find image URL for series {0}'.format(series_id), xbmc.LOGWARNING)
    return None


def list_streams(listing, streams, offset_url, item_limit=25):
    """
    Create the list of playable streams in the Kodi interface.
    :param listing: list for the streams. Can include some fixed elements
    :param streams: json of streams to list
    :param offset_url: url that opens next page of streams
    :param item_limit: maximum number of items per page
    :return: None
    """
    # Iterate through the streams.
    for stream in streams:
        list_item = create_list_item_from_stream(stream)
        if list_item is None:
            continue
        # Create a URL for the plugin recursive callback.
        # Example: plugin://plugin.video.example/?action=play&video=http://www.vidsplay.com/vids/crab.mp4
        url = '{0}?action=play&stream={1}'.format(_url, stream['id'])
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the listing as a 3-element tuple.
        listing.append((url, list_item, is_folder))
    if len(listing) >= item_limit:
        list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
            get_color('menuItemColor'), get_translation(32008)))
        listing.append((offset_url, list_item, True))
    # Add our listing to Kodi.
    # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
    # instead of adding one by ove via addDirectoryItem.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)
    xbmcplugin.setContent(_handle, 'movies')


def create_list_item_from_stream(stream):
    info_labels = {}
    stream_info = {}
    context_menu = []
    list_item = None
    unplayable = False
    unplayable_marker_category = '[COLOR ' + get_color('unplayableColor') + ']!!![/COLOR] '
    unplayable_marker_drm = '[COLOR ' + get_color('unplayableColor') + ']!-![/COLOR] '
    # Create a list item with a text label and a thumbnail image.
    if 'subject' in stream:
        # Check if the stream is included in any of the unplayable categories
        category_id = ''
        for subject in stream['subject']:
            if subject['id'] in _unplayableCategories:
                unplayable = True
                category_id = subject['id']
                break
            if 'broader' in subject:
                if subject['broader']['id'] in _unplayableCategories:
                    unplayable = True
                    category_id = subject['broader']['id']
                    break
        if unplayable:
            if _addon.getSetting('showUnplayable') == 'false':
                log('Stream is unplayable. It is in category: {0}'.format(category_id))
                return
    for language_code in get_language_codes():
        if language_code in stream['title']:
            if unplayable:
                list_item = xbmcgui.ListItem(
                    label=unplayable_marker_category + str(stream['title'][language_code].encode('utf-8')) + ' ')
            else:
                list_item = xbmcgui.ListItem(label=str(stream['title'][language_code].encode('utf-8')) + ' ')
            break
    if list_item is None:
        log('no title for stream: {0}'.format(stream['title']), xbmc.LOGWARNING)
        return
    if 'available' in stream['image']:
        if stream['image']['available']:
            image_url = '{0}/{1}/{2}.{3}'.format(
                _image_cdn_url, _image_transformation, stream['image']['id'], 'png')
            list_item.setThumbnailImage(image_url)
    for language_code in get_language_codes():
        if language_code in stream['description']:
            info_labels['plot'] = stream['description'][language_code].encode('utf-8')
            break
    if 'promotionTitle' in stream:
        for language_code in get_language_codes():
            if language_code in stream['promotionTitle']:
                info_labels['tagline'] = stream['promotionTitle'][language_code].encode('utf-8')
                break
    if 'duration' in stream:
        duration = get_timedelta_from_duration(stream['duration'])
        # The total_seconds function was introduced in Python 2.7
        if duration is not None and 'total_seconds' in dir(duration):
            info_labels['duration'] = duration.total_seconds()
            stream_info = {'duration': duration.total_seconds()}
    if 'partOfSeason' in stream or 'episodeNumber' in stream:
        season_string = ''
        episode_string = ''
        if 'partOfSeason' in stream:
            if 'seasonNumber' in stream['partOfSeason']:
                season_number = stream['partOfSeason']['seasonNumber']
                info_labels['season'] = season_number
                season_string = 'S{0}'.format(str(season_number))
        if 'episodeNumber' in stream:
            episode_number = stream['episodeNumber']
            info_labels['episode'] = episode_number
            episode_string = 'E{0}'.format(str(episode_number))
        list_item.setLabel('{0} - {1}{2}'.format(list_item.getLabel(), season_string, episode_string))
    if 'itemTitle' in stream:
        for language_code in get_language_codes():
            if language_code in stream['itemTitle']:
                list_item.setLabel('{0} - {1}'.format(list_item.getLabel(),
                                                      stream['itemTitle'][language_code].encode('utf-8')))
                break
    if 'partOfSeries' in stream:
        if 'id' in stream['partOfSeries']:
            series_title = 'SERIES TITLE NOT FOUND'
            if 'title' in stream['partOfSeries']:
                for language_code in get_language_codes():
                    if language_code in stream['partOfSeries']['title']:
                        series_title = stream['partOfSeries']['title'][language_code]
                        break
            add_series_favourite_context_menu_item = \
                (get_translation(32027),
                 'RunPlugin({0}?action=add_favourite&type=series&id={1}&label={2})'
                 .format(_url, stream['partOfSeries']['id'], series_title.encode('utf-8')))
            context_menu.append(add_series_favourite_context_menu_item)
    found_current_publication = False
    for publication in stream['publicationEvent']:
        if publication['temporalStatus'] == 'currently' and publication['type'] == 'OnDemandPublication':
            if _addon.getSetting("inFinland") == "false" and publication['region'] == 'Finland':
                # We need to skip publications that can only be seen in Finland
                continue
            if _addon.getSetting("showUnplayable") == "true":
                content_protection_id = publication["media"]["contentProtection"][0]["id"]
                if content_protection_id == '22-2' or content_protection_id == '22-3':
                    list_item.setLabel('{0}{1}'.format(unplayable_marker_drm, list_item.getLabel()))
            found_current_publication = True
            if 'startTime' in publication and 'endTime' in publication:
                light_tag_open = ''
                light_tag_close = ''
                bold_tag_open = ''
                bold_tag_close = ''
                if int(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version').split('.', 1)[0]) > 15:
                    light_tag_open = '[LIGHT]'
                    light_tag_close = '[/LIGHT]'
                if _addon.getSetting("boldTitles") == "true":
                    bold_tag_open = '[B]'
                    bold_tag_close = '[/B]'
                if _addon.getSetting('showExtraInfo') == 'true':
                    list_item.setLabel('{0}{1}'.format(list_item.getLabel(), '[CR]'))
                    out_format = '%d.%m.%Y'
                    start_time = time.strptime(publication['startTime'].split('+')[0], _yle_time_format)
                    start_time = time.strftime(out_format, start_time)
                    end_time = time.strptime(publication['endTime'].split('+')[0], _yle_time_format)
                    end_time = time.strftime(out_format, end_time)
                    # Example: '[B][COLOR grey]Program - S1E1[/COLOR][/B]
                    # [LIGHT][COLOR grey]1.1.2016 until 1.1.2017[/COLOR][/LIGHT]'
                    list_item.setLabel('{0}[COLOR {1}]{2}[/COLOR]{3}{4}[COLOR {5}]{6} | {7} {8}[/COLOR]{9}'.
                                       format(bold_tag_open, get_color('titleColor'), list_item.getLabel(),
                                              bold_tag_close, light_tag_open, get_color('dateColor'), start_time,
                                              get_translation(32054), end_time, light_tag_close))
                else:
                    ttl = time.strptime(publication['endTime'].split('+')[0], _yle_time_format)
                    now = time.strptime(time.strftime(_yle_time_format), _yle_time_format)
                    ttl = (ttl.tm_year - now.tm_year) * 365 + ttl.tm_yday - now.tm_yday
                    # Example: '[B][COLOR grey]Program - S1E1[/COLOR][/B] |
                    # [LIGHT][COLOR grey]30 d remaining[/COLOR][/LIGHT]'
                    list_item.setLabel("{0}[COLOR {1}]{2}[/COLOR]{3} | {4}[COLOR {5}]{6} {7}[/COLOR]{8} ".
                                       format(bold_tag_open, get_color('titleColor'), list_item.getLabel(),
                                              bold_tag_close, light_tag_open, get_color('dateColor'), str(ttl),
                                              get_translation(32055), light_tag_close))
            break
    if not found_current_publication:
        log("No publication with 'currently': {0}".format(stream['title']), xbmc.LOGWARNING)
        return
    add_favourite_context_menu_item = (get_translation(32026),
                                       'RunPlugin({0}?action=add_favourite&type=episode&id={1}&label={2})'.
                                       format(_url, stream['id'], list_item.getLabel()))
    context_menu.append(add_favourite_context_menu_item)
    # Set 'IsPlayable' property to 'true'.
    # This is mandatory for playable items!
    list_item.setProperty('IsPlayable', 'true')
    list_item.setInfo(type='Video', infoLabels=info_labels)
    list_item.addStreamInfo('video', stream_info)
    list_item.addContextMenuItems(context_menu)
    return list_item


def play_stream(path):
    """
    Play a stream by the provided path.
    :param path: stream id
    :return: None
    """
    data = get_item(path)
    report_url = None
    subtitle_list = []
    for publication in data['publicationEvent']:
        if publication['temporalStatus'] == 'currently' and publication['type'] == 'OnDemandPublication':
            log("Found correct publication, media id: " + publication['media']['id'])
            media_id = publication['media']['id']
            report_url = get_report_url(path, media_id)
            protocol = 'HLS'
            media_is_audio = publication['media']['type'] == 'AudioObject'
            if media_is_audio:
                protocol = 'PMD'
            playout_data = get_playout(path, media_id, protocol)
            encrypted_url = playout_data[0]['url']
            subtitles = playout_data[0]['subtitles']
            for subtitle in subtitles:
                subtitle_list.append(subtitle['uri'])
            path = decrypt_url(encrypted_url)
            log("decrypted path: " + path)
            if int(_addon.getSetting("maxResolution")) > 0 and not media_is_audio:
                path = get_resolution_specific_url(path)
                log("modified path: " + path)
            break
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    play_item.setSubtitles(subtitle_list)
    # Report usage to YLE
    response = get_url_response(report_url)
    if response.getcode() != 200:
        log("Could not report usage. Got code {0}".format(response.getcode()), xbmc.LOGWARNING)
    if _addon.getSetting("noSubtitlesForDefaultLangAudio") == 'true':
        disable_subtitles = False
        if 'audio' in data:
            for audio in data['audio']:
                if 'language' in audio:
                    for language in audio['language']:
                        if language == get_language_codes()[0]:
                            disable_subtitles = True
        if disable_subtitles:
            xbmcplugin.endOfDirectory(_handle, True, False, False)
            player = xbmc.Player()
            player.play(item=path, listitem=play_item)
            tries = 10
            while tries > 0:
                time.sleep(1)
                tries -= 1
                if player.isPlaying():
                    break
            player.showSubtitles(False)
            return
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def get_resolution_specific_url(path):
    """
    Use the master url to get the correct resolution specific url.
    This method is not working anymore since the url format has been changed.
    :param path: path to master.m3u8
    :return: resolution specific path
    """
    # TODO Redo this method to work with current m3u8 version
    return path


def live_tv_channels(path=None):
    if not path:
        listing = []
        yle_1 = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(get_color('menuItemColor'), 'YLE TV1'))
        yle_1_url = '{0}?action=live&path={1}'.format(_url, _yle_tv1_live_url)
        yle_1.setProperty('IsPlayable', 'true')
        listing.append((yle_1_url, yle_1, False))
        yle_2 = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(get_color('menuItemColor'), 'YLE TV2'))
        yle_2_url = '{0}?action=live&path={1}'.format(_url, _yle_tv2_live_url)
        yle_2.setProperty('IsPlayable', 'true')
        listing.append((yle_2_url, yle_2, False))
        for service in _tv_services:
            service_name = service.replace('-', ' ').title()
            data = get_areena_api_json_data('programs/schedules', 'now.json', ['service=' + service])
            for item in data:
                content = item['content']
                for language_code in get_language_codes():
                    if language_code in content['title']:
                        content['title'][language_code] = \
                            service_name + ': ' + content['title'][language_code]
                list_item = create_list_item_from_stream(content)
                if list_item:
                    url = '{0}?action=play&stream={1}'.format(_url, content['id'])
                    listing.append((url, list_item, False))
                else:
                    title = ''
                    for language_code in get_language_codes():
                        if language_code in content['title']:
                            title = ' - ' + content['title'][language_code]
                            break
                    not_available_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
                        get_color('menuItemColor'),  get_translation(32072) + title.encode('utf-8')))
                    not_available_item.setProperty('IsPlayable', 'false')
                    listing.append((None, not_available_item, False))
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(_handle)
    else:
        xbmcplugin.setResolvedUrl(
            _handle, True, listitem=xbmcgui.ListItem(path=get_resolution_specific_url_for_live_tv(path)))


def get_resolution_specific_url_for_live_tv(path):
    """
    Use the master url to get the correct resolution specific url.
    :param path: path to master.m3u8
    :return: resolution specific path
    """
    max_resolution = int(_addon.getSetting("maxResolution"))
    if max_resolution == 2:
        bandwidth = 184
    elif max_resolution == 3:
        bandwidth = 364
    elif max_resolution == 4:
        bandwidth = 664
    elif max_resolution == 5:
        bandwidth = 1064
    elif max_resolution == 6:
        bandwidth = 1564
    else:
        return path
    replace_url = 'index_{0}_av-p.m3u8?sd=10&rebase=on'.format(bandwidth)
    return path.replace('master.m3u8', replace_url)


def search(search_string=None, offset=0, clear_search=False, remove_string=None):
    """
    Manage the search view.
    :param search_string: string to search
    :param offset: offset of the results
    :param clear_search: if true, will clear earlier searches
    :param remove_string: if not 'None' will remove the given string
    :return: None
    """
    if clear_search:
        _addon.setSetting("searches", "")
    if search_string is None:
        log("Show search UI")
        listing = []
        new_search_list_item = xbmcgui.ListItem(label='[COLOR {0}][{1}][/COLOR]'.format(
            get_color('menuItemColor'), get_translation(32009)))
        new_search_url = '{0}?action=new_search&type=free'.format(_url)
        listing.append((new_search_url, new_search_list_item, True))
        new_series_search_list_item = xbmcgui.ListItem(label='[COLOR {0}][{1}][/COLOR]'.format(
            get_color('menuItemColor'), get_translation(32022)))
        new_series_search_url = '{0}?action=new_search&type=series'.format(_url)
        listing.append((new_series_search_url, new_series_search_list_item, True))
        clear_search_list_item = xbmcgui.ListItem(label='[COLOR {0}][{1}][/COLOR]'.format(
            get_color('menuItemColor'), get_translation(32010)))
        clear_search_url = '{0}?action=search&clear_search=1'.format(_url)
        listing.append((clear_search_url, clear_search_list_item, True))
        searches = _addon.getSetting("searches").splitlines()
        if remove_string is not None:
            if remove_string in searches:
                searches.remove(remove_string)
                _addon.setSetting("searches", "\n".join(searches))
        for search_item in searches:
            search_type, query = search_item.split(':', 1)
            if search_type == 'free':
                search_list_item = xbmcgui.ListItem(label="[COLOR {0}]{1}[/COLOR]{2}".format(
                    get_color('freeSearchColor'), get_translation(32023), query))
            else:
                search_list_item = xbmcgui.ListItem(label="[COLOR {0}]{1}[/COLOR]{2}".format(
                    get_color('seriesSearchColor'), get_translation(32024), query))
            search_url = '{0}?action=search&search_string={1}'.format(_url, search_item)
            context_menu = []
            remove_context_menu_item = \
                (get_translation(32029), 'ActivateWindow(Videos,{0}?action=search&remove_string={1})'.
                 format(_url, search_item))
            context_menu.append(remove_context_menu_item)
            search_list_item.addContextMenuItems(context_menu)
            listing.append((search_url, search_list_item, True))
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    else:
        log(search_string)
        searches = _addon.getSetting("searches").splitlines()
        if searches.count(search_string) > 0:
            searches.remove(search_string)
        searches.insert(0, search_string)
        if len(searches) > 20:
            searches.pop()
        _addon.setSetting("searches", "\n".join(searches))

        search_type, query = search_string.split(':', 1)
        if search_type == 'free':
            result = get_items(offset, query=query)
            search_url = '{0}?action=search&search_string={1}&offset={2}'.format(_url, search_string, offset + 25)
            list_streams([], result, search_url)
        else:
            result = {'data': []}
            while True:
                data = get_items(offset, query=query, limit='100')
                for item in data:
                    result['data'].append(item)
                offset += 100
                if len(data) < 100:
                    break
            log(result)
            list_of_series = {}
            listing = []
            for item in result['data']:
                if 'partOfSeries' in item:
                    if 'title' in item['partOfSeries']:
                        for language_code in get_language_codes():
                            if language_code in item['partOfSeries']['title']:
                                title = item['partOfSeries']['title'][language_code]
                                if query.decode('utf-8').lower() in title.lower():
                                    list_of_series[item['partOfSeries']['id']] = \
                                        item['partOfSeries']['title'][language_code]
                                break
            for key in list_of_series:
                series_list_item = xbmcgui.ListItem(label=list_of_series[key])
                series_url = '{0}?action=series&series_id={1}&offset={2}'.format(_url, key, 0)
                image_url = get_image_url_for_series(key)
                if image_url:
                    series_list_item.setThumbnailImage(image_url)
                listing.append((series_url, series_list_item, True))
            xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    xbmcplugin.endOfDirectory(_handle)


def new_search(search_type):
    """
    Creates a new search. Saves it to add-on settings
    :param search_type 'free' for free search, 'series' for searching series names
    :return: None
    """
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText() != '':
        search_text = "{0}:{1}".format(search_type, keyboard.getText())
        search(search_text, 0)
    xbmcplugin.endOfDirectory(_handle)


def favourites(favourites_folder="favourites"):
    listing = []
    items = _addon.getSetting(favourites_folder).splitlines()
    items = sort_favourites(items)
    for favourite in items:
        fav_type, fav_id, fav_label = favourite.split(':', 2)
        favourite_list_item = xbmcgui.ListItem(label=fav_label)
        if fav_type == 'series':
            favourite_url = '{0}?action=series&series_id={1}&offset={2}'.format(_url, fav_id, 0)
            image_url = get_image_url_for_series(fav_id)
            if image_url:
                if image_url == 'NO_ITEMS':
                    favourite_list_item.setLabel('{0} [COLOR red]{1}[/COLOR]'.format(
                        favourite_list_item.getLabel(), get_translation(32072)))
                else:
                    favourite_list_item.setThumbnailImage(image_url)
            is_folder = True
        elif fav_type == 'episode':
            list_item = create_list_item_from_stream(get_item(fav_id))
            if list_item is None:
                favourite_url = '{0}?action=favourites&folder={1}'.format(_url, favourites_folder)
                image_url = '{0}/{1}/13-{2}.{3}'.format(_image_cdn_url, _image_transformation, fav_id, 'png')
                favourite_list_item.setThumbnailImage(image_url)
                favourite_list_item.setLabel('{0} [COLOR red]{1}[/COLOR]'.format(
                    favourite_list_item.getLabel(), get_translation(32072)))
                is_folder = True
            else:
                favourite_url = '{0}?action=play&stream={1}'.format(_url, fav_id)
                favourite_list_item = list_item
                is_folder = False
        elif fav_type == 'folder':
            favourite_list_item.setLabel('[B]' + fav_label.replace('favFolder', '').upper() + '[/B]')
            favourite_url = '{0}?action=favourites&folder={1}'.format(_url, fav_label)
            is_folder = True
        else:
            raise ValueError("Unknown favourites type '{0}'".format(fav_type))
        context_menu = []
        remove_favourite_context_menu_item = (
            get_translation(32028),
            'ActivateWindow(Videos,{0}?action=remove_favourite&type={1}&id={2}&label={3}&folder={4})'.
            format(_url, fav_type, fav_id, fav_label, favourites_folder))
        context_menu.append(remove_favourite_context_menu_item)
        for possible_folder in items:
            folder_fav_type, folder_fav_id, folder_fav_label = possible_folder.split(':', 2)
            if folder_fav_type == 'folder' and fav_label != folder_fav_label:
                move_favourite_context_menu_item = (
                    '{0} {1}'.format(get_translation(32069), folder_fav_label.replace('favFolder', '').upper()),
                    'ActivateWindow(Videos,{0}?action=move_favourite&type={1}&id={2}&label={3}&from={4}&to={5})'.
                    format(_url, fav_type, fav_id, fav_label, favourites_folder, folder_fav_label))
                context_menu.append(move_favourite_context_menu_item)
        if favourites_folder != 'favourites':
            move_to_parent_folder_context_menu_item = (
                get_translation(32070),
                'ActivateWindow(Videos,{0}?action=move_favourite&type={1}&id={2}&label={3}&from={4}&to={5})'.
                format(_url, fav_type, fav_id, fav_label, favourites_folder,
                       get_parent_folder('favourites', favourites_folder)))
            context_menu.append(move_to_parent_folder_context_menu_item)
        favourite_list_item.addContextMenuItems(context_menu)
        listing.append((favourite_url, favourite_list_item, is_folder))
    add_folder_list_item = xbmcgui.ListItem(label=get_translation(32071))
    listing.append(('{0}?action=add_favourites_folder&folder={1}'.format(_url, favourites_folder),
                    add_folder_list_item, True))
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    xbmcplugin.endOfDirectory(_handle)


def sort_favourites(favourites_list):
    folders = []
    series = []
    items = []
    sorted_items = []
    for favourite in favourites_list:
        fav_type, fav_id, fav_label = favourite.split(':', 2)
        if fav_type == 'series':
            series.append(favourite)
        elif fav_type == 'episode':
            items.append(favourite)
        elif fav_type == 'folder':
            folders.append(favourite)
    sorted_items.extend(sorted(folders, key=lambda fav: fav.split(':', 2)[2]))
    sorted_items.extend(sorted(series, key=lambda fav: fav.split(':', 2)[2]))
    sorted_items.extend(sorted(items, key=lambda fav: fav.split(':', 2)[2]))
    return sorted_items


def add_favourite(fav_type, fav_id, fav_label, fav_folder="favourites"):
    items = _addon.getSetting(fav_folder).splitlines()
    items.insert(0, '{0}:{1}:{2}'.format(fav_type, fav_id, fav_label))
    _addon.setSetting(fav_folder, "\n".join(items))


def remove_favourite(fav_type, fav_id, fav_label, fav_folder):
    item_found = False
    items = _addon.getSetting(fav_folder).splitlines()
    favourite = '{0}:{1}:{2}'.format(fav_type, fav_id, fav_label)
    if favourite in items:
        items.remove(favourite)
        if fav_type == 'folder':
            _addon.setSetting(fav_label, None)
        item_found = True
    _addon.setSetting(fav_folder, "\n".join(items))
    favourites(fav_folder)
    return item_found


def add_favourites_folder(fav_folder):
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText() != '':
        folder_name = 'favFolder' + keyboard.getText()
        if favourite_folder_exists('favourites', folder_name):
            pass
        else:
            _addon.setSetting(folder_name, "")
            add_favourite('folder', '0', folder_name, fav_folder)
    xbmcplugin.endOfDirectory(_handle)


def favourite_folder_exists(search_folder, target_folder):
    items = _addon.getSetting(search_folder).splitlines()
    for favourite in items:
        fav_type, fav_id, fav_label = favourite.split(':', 2)
        if fav_type == 'folder':
            if fav_label.upper() == target_folder.upper():
                return True
            else:
                exists = favourite_folder_exists(fav_label, target_folder)
                if exists:
                    return True
    return False


def get_parent_folder(search_folder, target_label):
    items = _addon.getSetting(search_folder).splitlines()
    for favourite in items:
        fav_type, fav_id, fav_label = favourite.split(':', 2)
        if fav_type == 'folder':
            if fav_label.upper() == target_label.upper():
                return search_folder
            else:
                parent = get_parent_folder(fav_label, target_label)
                if parent is not None:
                    return parent
        else:
            if fav_label == target_label:
                return search_folder
    return None


def move_favourite_to_folder(fav_type, fav_id, fav_label, fav_old_folder, fav_new_folder):
    items = ''
    if fav_type == 'folder':
        items = _addon.getSetting(fav_label)
    item_found = remove_favourite(fav_type, fav_id, fav_label, fav_old_folder)
    if item_found:
        add_favourite(fav_type, fav_id, fav_label, fav_new_folder)
        if fav_type == 'folder':
            _addon.setSetting(fav_label, items)


def decrypt_url(encrypted_url):
    enc = base64.b64decode(encrypted_url)
    iv = enc[:16]
    try:
        from Crypto.Cipher import AES
    except ImportError:
        import pyaes as AES
    cipher = AES.new(get_secret_key(), AES.MODE_CBC, iv)
    decrypted_url = cipher.decrypt(enc[16:])
    unpadded_url = decrypted_url[:-ord(decrypted_url[len(decrypted_url)-1:])]
    return unpadded_url


def get_app_id():
    app_id = _addon.getSetting("appID")
    if app_id == '':
        try:
            import credentials
            app_id = credentials._appId
        except ImportError:
            credentials = None
            log('Could not find the app_id. Either set it from the setting menu or create credentials.py file.',
                xbmc.LOGWARNING)
    return app_id


def get_app_key():
    app_key = _addon.getSetting("appKey")
    if app_key == '':
        try:
            import credentials
            app_key = credentials._appKey
        except ImportError:
            credentials = None
            log('Could not find the app_key. Either set it from the setting menu or create credentials.py file.',
                xbmc.LOGWARNING)
    return app_key


def get_secret_key():
    secret_key = _addon.getSetting("secretKey")
    if secret_key == '':
        try:
            import credentials
            secret_key = credentials._secretKey
        except ImportError:
            credentials = None
            log('Could not find the secret_key. Either set it from the setting menu or create credentials.py file.',
                xbmc.LOGWARNING)
    return secret_key


def get_url_response(url):
    try:
        return urllib.urlopen(url)
    except IOError as error:
        if 'CERTIFICATE_VERIFY_FAILED' in error.message:
            # The certificate was not found. Let's try without verification.
            import ssl
            return urllib.urlopen(url, context=ssl._create_unverified_context())
        elif 'http error' in error.message:
            log('The url [{0}] could not be opened! Error: {1}'.format(url, error.message), xbmc.LOGERROR)
            log('Is the url valid and is the site reachable?', xbmc.LOGERROR)
        raise error


def get_timedelta_from_duration(duration):
    log(duration)
    # From http://stackoverflow.com/a/2765366
    regex = re.compile('(?P<sign>-?)P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)'
                       'H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?')
    # Fetch the match groups with default value of 0 (not None)
    duration = regex.match(duration).groupdict(0)

    # Create the timedelta object from extracted groups
    delta = datetime.timedelta(days=int(duration['days']) + (int(duration['months']) * 30) +
                               (int(duration['years']) * 365), hours=int(duration['hours']),
                               minutes=int(duration['minutes']), seconds=int(duration['seconds']))
    log(delta)
    return delta


def get_language_codes():
    language = int(_addon.getSetting("language"))
    if language == 0:
        return ['fi', 'sv', 'en']
    elif language == 1:
        return ['sv', 'fi', 'en']
    elif language == 2:
        return ['en', 'fi', 'sv']
    raise ValueError('Unknown language {0}'.format(language))


def get_translation(translation_id):
    return _addon.getLocalizedString(translation_id).encode('utf-8')


def get_sort_method():
    sort_method = int(_addon.getSetting("sortMethod"))
    asc_or_desc = int(_addon.getSetting("ascOrDesc"))

    if asc_or_desc == 0:
        asc_or_desc = 'asc'
    elif asc_or_desc == 1:
        asc_or_desc = 'desc'
    else:
        raise ValueError('Unknown sort type {0}'.format(asc_or_desc))

    if sort_method == 0:
        sort_method = 'playcount.6h'
    elif sort_method == 1:
        sort_method = 'playcount.24h'
    elif sort_method == 2:
        sort_method = 'playcount.week'
    elif sort_method == 3:
        sort_method = 'playcount.month'
    elif sort_method == 4:
        sort_method = 'publication.starttime'
    elif sort_method == 5:
        sort_method = 'publication.endtime'
    elif sort_method == 6:
        sort_method = 'updated'
    else:
        raise ValueError('Unknown sort method {0}'.format(sort_method))

    return '{0}:{1}'.format(sort_method, asc_or_desc)


def get_color(setting):
    color = _addon.getSetting(setting)
    colors = ["aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black", "blanchedalmond",
              "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse", "chocolate", "coral",
              "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray",
              "darkgreen", "darkgrey", "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange", "darkorchid",
              "darkred", "darksalmon", "darkseagreen", "darkslateblue", "darkslategray", "darkslategrey",
              "darkturquoise", "darkviolet", "deeppink", "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick",
              "floralwhite", "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "green",
              "greenyellow", "grey", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender",
              "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
              "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey", "lightpink", "lightsalmon",
              "lightseagreen", "lightskyblue", "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow",
              "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue", "mediumorchid",
              "mediumpurple", "mediumseagreen", "mediumslateblue", "mediumspringgreen", "mediumturquoise",
              "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "none",
              "oldlace", "olive", "olivedrab", "orange", "orangered", "orchid", "palegoldenrod", "palegreen",
              "paleturquoise", "palevioletred", "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue",
              "purple", "red", "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell",
              "sienna", "silver", "skyblue", "slateblue", "slategray", "slategrey", "snow", "springgreen", "steelblue",
              "tan", "teal", "thistle", "tomato", "transparent", "turquoise", "violet", "wheat", "white", "whitesmoke",
              "yellow", "yellowgreen"]
    if _addon.getSetting('randomColors') == 'true':
        import random
        return random.choice(colors)
    if color not in colors:
        log('Unknown color "{0}."'.format(color), xbmc.LOGWARNING)
        log('Available colors: {0}'.format(colors))
        return 'black'
    return color


def show_menu():
    if get_app_id() == '' or get_app_key() == '' or get_secret_key() == '':
        return show_credentials_needed_menu()
    listing = []
    tv_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32031)))
    tv_url = '{0}?action=categories&base=5-130'.format(_url)
    listing.append((tv_url, tv_list_item, True))
    live_tv_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32067)))
    live_tv_url = '{0}?action=live'.format(_url)
    listing.append((live_tv_url, live_tv_list_item, True))
    radio_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32032)))
    radio_url = '{0}?action=categories&base=5-200'.format(_url)
    listing.append((radio_url, radio_list_item, True))
    search_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32007)))
    search_url = '{0}?action=search'.format(_url)
    listing.append((search_url, search_list_item, True))
    favourites_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32025)))
    favourites_url = '{0}?action=favourites'.format(_url)
    listing.append((favourites_url, favourites_list_item, True))
    open_settings_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32040)))
    open_settings_url = '{0}?action=settings'.format(_url)
    listing.append((open_settings_url, open_settings_list_item, True))
    # Add our listing to Kodi.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def show_credentials_needed_menu():
    listing = []
    missing_credentials_list_item = xbmcgui.ListItem(label=get_translation(32038))
    missing_credentials_url = '{0}'.format(_url)
    listing.append((missing_credentials_url, missing_credentials_list_item, True))
    open_settings_list_item = xbmcgui.ListItem(label=get_translation(32039))
    open_settings_url = '{0}?action=settings'.format(_url)
    listing.append((open_settings_url, open_settings_list_item, True))
    # Add our listing to Kodi.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def router(param_string):
    """
    Router function that calls other functions
    depending on the provided param_string
    :param param_string:
    :return:
    """
    # Parse a URL-encoded param_string to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(param_string))
    log(params)

    # Check the parameters passed to the plugin
    if params:
        offset = 0
        if 'offset' in params:
            offset = int(params['offset'])
        if params['action'] == 'listing':
            # Display the list of streams in a provided category.
            streams = get_items(offset, category=params['category'])
            url = '{0}?action=listing&category={1}&offset={2}'.format(_url, params['category'], (offset + 25))
            sub_categories = []
            if offset == 0:
                sub_categories = list_sub_categories(params['category'])
            list_streams(sub_categories, streams, url)
        elif params['action'] == 'play':
            # Play a stream from a provided URL.
            play_stream(params['stream'])
        elif params['action'] == 'search':
            search_string = None
            if 'search_string' in params:
                search_string = str(params['search_string'])
            clear_search = False
            if 'clear_search' in params:
                clear_search = bool(params['clear_search'])
            remove_string = None
            if 'remove_string' in params:
                remove_string = str(params['remove_string'])
            # Show search window
            search(search_string=search_string, offset=offset, clear_search=clear_search, remove_string=remove_string)
        elif params['action'] == 'favourites':
            if 'folder' in params:
                favourite_folder = params['folder']
                favourites(favourite_folder)
            else:
                favourites()
        elif params['action'] == 'new_search':
            search_type = params['type']
            # Show search window
            new_search(search_type)
        elif params['action'] == 'add_favourite':
            favourite_type = params['type']
            favourite_id = params['id']
            favourite_label = params['label']
            add_favourite(favourite_type, favourite_id, favourite_label)
        elif params['action'] == 'remove_favourite':
            favourite_type = params['type']
            favourite_id = params['id']
            favourite_label = params['label']
            folder = params['folder']
            remove_favourite(favourite_type, favourite_id, favourite_label, folder)
        elif params['action'] == 'add_favourites_folder':
            favourite_folder = params['folder']
            add_favourites_folder(favourite_folder)
        elif params['action'] == 'move_favourite':
            favourite_type = params['type']
            favourite_id = params['id']
            favourite_label = params['label']
            old_folder = params['from']
            new_folder = params['to']
            move_favourite_to_folder(favourite_type, favourite_id, favourite_label, old_folder, new_folder)
        elif params['action'] == 'series':
            series_id = params['series_id']
            list_series(series_id, offset)
        elif params['action'] == 'categories':
            base_category = params['base']
            list_categories(base_category)
        elif params['action'] == 'live':
            path = None
            if 'path' in params:
                path = params['path']
            live_tv_channels(path)
        elif params['action'] == 'settings':
            _addon.openSettings()
        else:
            log("Unknown action: {0}".format(params['action']), xbmc.LOGERROR)
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the main menu
        show_menu()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
