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
        message = u'%s: %s' % (_addonid, txt)
        xbmc.log(msg=message.encode("utf-8"), level=log_level)


def get_categories():
    """
    Get a list of all the categories.
    :return: list
    """
    url = "https://external.api.yle.fi/v1/programs/categories.json?app_id=" + get_app_id() + "&app_key=" + get_app_key()
    return get_json(url)['data']


def get_streams(category, offset):
    """
    Get the list of streams.
    :param category: category id
    :param offset: offset for streams to retrieve
    :return: json data of the streams
    """

    url = "https://external.api.yle.fi/v1/programs/items.json?" \
          "availability=ondemand" \
          "&category=" + category + \
          get_media_type() + \
          "&order=" + get_sort_method() + \
          "&contentprotection=22-0,22-1" \
          "&offset=" + str(offset) + \
          get_region() + \
          "&app_id=" + get_app_id() + "&app_key=" + get_app_key()
    return get_json(url)['data']


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
                        category_title = '[COLOR red]{0}[/COLOR]'.format(category['title'][language_code].
                                                                         encode('utf-8'))
                    else:
                        category_title = category['title'][language_code].encode('utf-8')
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
    result = get_json("https://external.api.yle.fi/v1/programs/items.json?series={0}&offset={1}&order={2}"
                      "&availability=ondemand{3}&app_id={4}&app_key={5}"
                      .format(series_id, offset, get_sort_method(), get_region(), get_app_id(), get_app_key()))
    series_url = '{0}?action=series&series_id={1}&offset={2}'.format(_url, series_id, offset + 25)
    list_streams([], result['data'], series_url)


def list_streams(listing, streams, offset_url):
    """
    Create the list of playable streams in the Kodi interface.
    :param listing: list for the streams. Can include some fixed elements
    :param streams: json of streams to list
    :param offset_url: url that opens next page of streams
    :return: None
    """
    # Iterate through the streams.
    for stream in streams:
        info_labels = ()
        stream_info = {}
        context_menu = []
        list_item = None
        unplayable = False
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
                    continue
        for language_code in get_language_codes():
            if language_code in stream['title']:
                if unplayable:
                    list_item = xbmcgui.ListItem(label='[COLOR red]!!![/COLOR] ' + str(stream['title'][language_code].
                                                                                       encode('utf-8')) + ' ')
                else:
                    list_item = xbmcgui.ListItem(label=str(stream['title'][language_code].encode('utf-8')) + ' ')
                break
        if list_item is None:
            log('no title for stream: {0}'.format(stream['title']), xbmc.LOGWARNING)
            break
        if 'available' in stream['image']:
            if stream['image']['available']:
                image_url = 'http://images.cdn.yle.fi/image/upload/w_240,h_240,c_fit/{0}.png'.format(
                    stream['image']['id'])
                list_item.setThumbnailImage(image_url)
        for language_code in get_language_codes():
            if language_code in stream['description']:
                info_labels = info_labels + ('plot', stream['description'][language_code].encode('utf-8'))
                break
        if 'duration' in stream:
            duration = get_timedelta_from_duration(stream['duration'])
            if duration is not None:
                info_labels = info_labels + ('duration', duration.total_seconds())
                stream_info = {'duration': duration.total_seconds()}
        if 'partOfSeason' in stream or 'episodeNumber' in stream:
            season_string = ''
            episode_string = ''
            if 'partOfSeason' in stream:
                if 'seasonNumber' in stream['partOfSeason']:
                    season_number = stream['partOfSeason']['seasonNumber']
                    info_labels = info_labels + ('season', season_number)
                    season_string = 'S{0}'.format(str(season_number))
            if 'episodeNumber' in stream:
                episode_number = stream['episodeNumber']
                info_labels = info_labels + ('episode', episode_number)
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
                found_current_publication = True
                if 'startTime' in publication and 'endTime' in publication:
                    if _addon.getSetting('showExtraInfo') == 'true':
                        list_item.setLabel('{0}{1}'.format(list_item.getLabel(), '[CR]'))
                        out_format = '%d-%m-%Y %H:%M:%S'
                        start_time = time.strptime(publication['startTime'].split('+')[0], _yle_time_format)
                        start_time = time.strftime(out_format, start_time)
                        end_time = time.strptime(publication['endTime'].split('+')[0], _yle_time_format)
                        end_time = time.strftime(out_format, end_time)
                        list_item.setLabel('{0} [COLOR red]{1} - {2}[/COLOR]'.format(list_item.getLabel(), start_time,
                                                                                     end_time))
                    else:
                        ttl = time.strptime(publication['endTime'].split('+')[0], _yle_time_format)
                        now = time.strptime(time.strftime(_yle_time_format), _yle_time_format)
                        ttl = (ttl.tm_year - now.tm_year) * 365 + ttl.tm_yday - now.tm_yday
                        list_item.setLabel("[COLOR red]{0}d[/COLOR] {1}".format(str(ttl), list_item.getLabel()))
                break
        if not found_current_publication:
            log("No publication with 'currently': {0}".format(stream['title']), xbmc.LOGWARNING)
            continue
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
        # Create a URL for the plugin recursive callback.
        # Example: plugin://plugin.video.example/?action=play&video=http://www.vidsplay.com/vids/crab.mp4
        url = '{0}?action=play&stream={1}'.format(_url, stream['id'])
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the listing as a 3-element tuple.
        listing.append((url, list_item, is_folder))

    if len(listing) > 24:
        list_item = xbmcgui.ListItem(label=get_translation(32008))
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


def play_stream(path):
    """
    Play a stream by the provided path.
    :param path: stream id
    :return: None
    """
    url = "https://external.api.yle.fi/v1/programs/items/" + path + ".json?app_id=" + get_app_id() + \
          "&app_key=" + get_app_key()
    report_url = None
    data = get_json(url)['data']
    subtitle_list = []
    for publication in data['publicationEvent']:
        if publication['temporalStatus'] == 'currently' and publication['type'] == 'OnDemandPublication':
            log("Found correct publication, media id: " + publication['media']['id'])
            protocol = 'HLS'
            if publication['media']['type'] == 'AudioObject':
                protocol = 'PMD'
            url = "https://external.api.yle.fi/v1/media/playouts.json?" \
                  "program_id=" + path + \
                  "&media_id=" + publication['media']['id'] + \
                  "&protocol=" + protocol + \
                  "&app_id=" + get_app_id() + \
                  "&app_key=" + get_app_key()
            report_url = "https://external.api.yle.fi/v1/tracking/streamstart?program_id={0}&media_id={1}&app_id={2}&" \
                         "app_key={3}".format(path, publication['media']['id'], get_app_id(), get_app_key())
            playout_data = get_json(url)
            encrypted_url = playout_data['data'][0]['url']
            subtitles = playout_data['data'][0]['subtitles']
            for subtitle in subtitles:
                subtitle_list.append(subtitle['uri'])
            path = decrypt_url(encrypted_url)
            break
    log("decrypted path: " + path)
    if int(_addon.getSetting("maxResolution")) > 0:
        path = get_resolution_specific_url(path)
        log("modified path: " + path)
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    play_item.setSubtitles(subtitle_list)
    # Report usage to YLE
    response = urllib.urlopen(report_url)
    if response.getcode() != 200:
        log("Could not report usage. Got code {0}".format(response.getcode()), xbmc.LOGWARNING)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def get_resolution_specific_url(path):
    """
    Use the master url to get the correct resolution specific url.
    :param path: path to master.m3u8
    :return: resolution specific path
    """
    response = urllib.urlopen(path).read()
    log(response)
    resolution_urls = []
    for line in response.split('\n'):
        if line.startswith('http'):
            resolution_urls.append(line)
    max_resolution = int(_addon.getSetting("maxResolution")) - 2
    if max_resolution < 0:
        return path.replace('master.m3u8', 'index_0_a.m3u8')
    for resolution in xrange(max_resolution, 0, -1):
        for resolution_url in resolution_urls:
            if 'index_{0}_av.m3u8'.format(resolution) in resolution_url:
                path = '{0}?{1}'.format(resolution_url.split('?', 1)[0], path.split('?', 1)[1])
                return path
    raise RuntimeError('Could not find resolution specific url with resolution setting {0}'.format(max_resolution))


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
        new_search_list_item = xbmcgui.ListItem(label='[' + get_translation(32009) + ']')
        new_search_url = '{0}?action=new_search&type=free'.format(_url)
        listing.append((new_search_url, new_search_list_item, True))
        new_series_search_list_item = xbmcgui.ListItem(label='[' + get_translation(32022) + ']')
        new_series_search_url = '{0}?action=new_search&type=series'.format(_url)
        listing.append((new_series_search_url, new_series_search_list_item, True))
        clear_search_list_item = xbmcgui.ListItem(label='[' + get_translation(32010) + ']')
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
                search_list_item = xbmcgui.ListItem(label="[COLOR green]" + get_translation(32023) + "[/COLOR]" + query)
            else:
                search_list_item = xbmcgui.ListItem(label="[COLOR red]" + get_translation(32024) + "[/COLOR]" + query)
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
            result = get_json("https://external.api.yle.fi/v1/programs/items.json?q={0}&offset={1}&order={2}"
                              "&availability=ondemand{3}&app_id={4}&app_key={5}"
                              .format(query, offset, get_sort_method(), get_region(), get_app_id(), get_app_key()))
            search_url = '{0}?action=search&search_string={1}&offset={2}'.format(_url, search_string, offset + 25)
            list_streams([], result['data'], search_url)
        else:
            result = {'data': []}
            while True:
                data = get_json("https://external.api.yle.fi/v1/programs/items.json?q={0}&offset={1}&order={2}"
                                "&availability=ondemand&limit=100{3}&app_id={4}&app_key={5}"
                                .format(query, offset, get_sort_method(), get_region(), get_app_id(), get_app_key()))
                for item in data['data']:
                    result['data'].append(item)
                offset += 100
                if len(data['data']) < 100:
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
                                if query.lower() in title.lower():
                                    list_of_series[item['partOfSeries']['id']] = \
                                        item['partOfSeries']['title'][language_code]
                                break
            for key in list_of_series:
                series_list_item = xbmcgui.ListItem(label=list_of_series[key])
                series_url = '{0}?action=series&series_id={1}&offset={2}'.format(_url, key, 0)
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


def favourites():
    listing = []
    items = _addon.getSetting("favourites").splitlines()
    for favourite in items:
        fav_type, fav_id, fav_label = favourite.split(':', 2)
        favourite_list_item = xbmcgui.ListItem(label=fav_label)
        if fav_type == 'series':
            favourite_url = '{0}?action=series&series_id={1}&offset={2}'.format(_url, fav_id, 0)
            is_folder = True
        elif fav_type == 'episode':
            favourite_url = '{0}?action=play&stream={1}'.format(_url, fav_id)
            favourite_list_item.setProperty('IsPlayable', 'true')
            is_folder = False
        else:
            raise ValueError("Unknown favourites type '{0}'".format(fav_type))
        context_menu = []
        remove_favourite_context_menu_item = \
            (get_translation(32028), 'ActivateWindow(Videos,{0}?action=remove_favourite&type={1}&id={2}&label={3})'.
             format(_url, fav_type, fav_id, fav_label))
        context_menu.append(remove_favourite_context_menu_item)
        favourite_list_item.addContextMenuItems(context_menu)
        listing.append((favourite_url, favourite_list_item, is_folder))
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    xbmcplugin.endOfDirectory(_handle)


def add_favourite(fav_type, fav_id, fav_label):
    items = _addon.getSetting("favourites").splitlines()
    items.insert(0, '{0}:{1}:{2}'.format(fav_type, fav_id, fav_label))
    _addon.setSetting("favourites", "\n".join(items))


def remove_favourite(fav_type, fav_id, fav_label):
    items = _addon.getSetting("favourites").splitlines()
    favourite = '{0}:{1}:{2}'.format(fav_type, fav_id, fav_label)
    if favourite in items:
        items.remove(favourite)
    _addon.setSetting("favourites", "\n".join(items))
    favourites()


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


def get_json(url):
    log(url)
    response = urllib.urlopen(url)
    log(response)
    if response is None or response == '':
        raise ValueError('Request "{0}" returned an empty response.'.format(url))
    data = json.loads(response.read())
    log(data)
    return data


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
    return _addon.getLocalizedString(translation_id)


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


def get_region():
    if _addon.getSetting("inFinland") == "true":
        return ''
    else:
        return '&region=world'


def get_media_type():
    if _addon.getSetting("showClips") == "true":
        return ''
    else:
        return '&type=program'


def show_menu():
    if get_app_id() == '' or get_app_key() == '' or get_secret_key() == '':
        return show_credentials_needed_menu()
    listing = []
    search_list_item = xbmcgui.ListItem(label='[' + get_translation(32007) + ']')
    search_url = '{0}?action=search'.format(_url)
    listing.append((search_url, search_list_item, True))
    favourites_list_item = xbmcgui.ListItem(label='[' + get_translation(32025) + ']')
    favourites_url = '{0}?action=favourites'.format(_url)
    listing.append((favourites_url, favourites_list_item, True))
    open_settings_list_item = xbmcgui.ListItem(label='[' + get_translation(32040) + ']')
    open_settings_url = '{0}?action=settings'.format(_url)
    listing.append((open_settings_url, open_settings_list_item, True))
    tv_list_item = xbmcgui.ListItem(label='[' + get_translation(32031) + ']')
    tv_url = '{0}?action=categories&base=5-130'.format(_url)
    listing.append((tv_url, tv_list_item, True))
    radio_list_item = xbmcgui.ListItem(label='[' + get_translation(32032) + ']')
    radio_url = '{0}?action=categories&base=5-200'.format(_url)
    listing.append((radio_url, radio_list_item, True))
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
            streams = get_streams(params['category'], offset)
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
            remove_favourite(favourite_type, favourite_id, favourite_label)
        elif params['action'] == 'series':
            series_id = params['series_id']
            list_series(series_id, offset)
        elif params['action'] == 'categories':
            base_category = params['base']
            list_categories(base_category)
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
