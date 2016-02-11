# -*- coding: utf-8 -*-
# Module: default
# Author: Samuli Lappi
# Created on: 2015-12-05

import sys
import urllib
import json
import base64
from Crypto.Cipher import AES
from urlparse import parse_qsl
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import credentials

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

_app_id = credentials._appId
_app_key = credentials._appKey
_secret_key = credentials._secretKey
_unplayableCategories = ["5-162", "5-164"]
_addonid = 'plugin.video.areena'
_addon = xbmcaddon.Addon(id=_addonid)


def log(txt, log_level=xbmc.LOGDEBUG):
    """
    Log something to the kodi.log file
    :param txt: Text to write to the log
    :param log_level: Severity of the log text
    :return: None
    """
    if (_addon.getSetting("debug") == "true") or (log_level != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (_addonid, txt)
        xbmc.log(msg=message.encode("utf-8"), level=log_level)


def get_categories():
    """
    Get the list of video categories.
    Here you can insert some parsing code that retrieves
    the list of video categories (e.g. 'Movies', 'TV-shows', 'Documentaries' etc.)
    from some site or server.
    :return: list
    """
    url = "https://external.api.yle.fi/v1/programs/categories.json?app_id=" + _app_id + "&app_key=" + _app_key
    return get_json(url)['data']


def get_videos(category, offset):
    """
    Get the list of videofiles/streams.
    Here you can insert some parsing code that retrieves
    the list of videostreams in a given category from some site or server.
    :param category: category id
    :param offset: offset for videos to retrieve
    :return: json data of the videos
    """

    url = "https://external.api.yle.fi/v1/programs/items.json?" \
          "availability=ondemand" \
          "&mediaobject=video" \
          "&category=" + category + \
          "&order=updated:desc" \
          "&contentprotection=22-0,22-1" \
          "&offset=" + str(offset) + \
          "&app_id=" + _app_id + "&app_key=" + _app_key
    return get_json(url)['data']


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    :return: None
    """
    # Get video categories
    categories = get_categories()
    # Create a list for our items.
    listing = []
    # Add static "categories"
    search_list_item = xbmcgui.ListItem(label='[Haku]')
    search_url = '{0}?action=search'.format(_url)
    listing.append((search_url, search_list_item, True))
    # Iterate through categories
    for category in categories:
        if 'broader' not in category:
            continue
        if 'id' not in category['broader']:
            continue
        if category['id'] in _unplayableCategories:
            continue

        if category['broader']['id'] == '5-130':
            # Create a list item with a text label and a thumbnail image.
            list_item = xbmcgui.ListItem(label=category['title']['fi'])
            # Set a fanart image for the list item.
            # Here we use the same image as the thumbnail for simplicity's sake.
            # list_item.setProperty('fanart_image', VIDEOS[category][0]['thumb'])
            # Set additional info for the list item.
            # Here we use a category name for both properties for for simplicity's sake.
            # setInfo allows to set various information for an item.
            # For available properties see the following link:
            # http://mirrors.xbmc.org/docs/python-docs/15.x-isengard/xbmcgui.html#ListItem-setInfo
            list_item.setInfo('video', {'title': category['title']['fi'], 'genre': category['type']})
            # Create a URL for the plugin recursive callback.
            url = '{0}?action=listing&category={1}'.format(_url, category['id'])
            # is_folder = True means that this item opens a sub-list of lower level items.
            is_folder = True
            # Add our item to the listing as a 3-element tuple.
            listing.append((url, list_item, is_folder))
    # Add our listing to Kodi.
    # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
    # instead of adding one by ove via addDirectoryItem.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_videos(videos, offset_url):
    """
    Create the list of playable videos in the Kodi interface.
    :param videos: json of videos to list
    :param offset_url: url that opens next page of videos
    :return: None
    """
    # Create a list for our items.
    listing = []
    # list.append(('{0}', '...', True))
    # Iterate through videos.
    for video in videos:
        # Create a list item with a text label and a thumbnail image.
        if 'fi' in video['title']:
            list_item = xbmcgui.ListItem(label=video['title']['fi'])
        else:
            log('no finnish title for video: {}'.format(video['title']), xbmc.LOGWARNING)

        # Set a fanart image for the list item.
        # Here we use the same image as the thumbnail for simplicity's sake.
        # list_item.setProperty('fanart_image', video['thumb'])
        # Set additional info for the list item.
        # if 'fi' in video['description']:
        #  list_item.setInfo('video', {'title': video['description']['fi']})
        # Set additional graphics (banner, poster, landscape etc.) for the list item.
        # Again, here we use the same image as the thumbnail for simplicity's sake.

        if 'available' in video['image']:
            # log("Available field exists")
            if video['image']['available']:
                image_url = 'http://images.cdn.yle.fi/image/upload/w_240,h_240,c_fit/{0}.png'.format(
                    video['image']['id'])
                # log("Image url is " + imageUrl)
                # list_item.setArt({'landscape': imageUrl})
                list_item.setThumbnailImage(image_url)
        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')
        # Create a URL for the plugin recursive callback.
        # Example: plugin://plugin.video.example/?action=play&video=http://www.vidsplay.com/vids/crab.mp4
        url = '{0}?action=play&video={1}'.format(_url, video['id'])
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the listing as a 3-element tuple.
        listing.append((url, list_item, is_folder))

    if len(listing) > 24:
        list_item = xbmcgui.ListItem(label="Next page")
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


def play_video(path):
    """
    Play a video by the provided path.
    :param path: video id
    :return: None
    """
    url = "https://external.api.yle.fi/v1/programs/items/" + path + ".json?app_id=" + _app_id + "&app_key=" + _app_key
    data = get_json(url)
    subtitle_list = []
    for publication in data['data']['publicationEvent']:
        log(publication['temporalStatus'])
        if publication['temporalStatus'] == 'currently':
            log("Found correct publication, media id: " + publication['media']['id'])
            url = "https://external.api.yle.fi/v1/media/playouts.json?" \
                  "program_id=" + path + \
                  "&media_id=" + publication['media']['id'] + \
                  "&protocol=HLS&app_id=" + _app_id + \
                  "&app_key=" + _app_key
            playout_data = get_json(url)
            encrypted_url = playout_data['data'][0]['url']
            subtitles = playout_data['data'][0]['subtitles']
            for subtitle in subtitles:
                subtitle_list.append(subtitle['uri'])
            path = decrypt_url(encrypted_url)
    log("decrypted path: " + path)
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    play_item.setSubtitles(subtitle_list)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def search(search_string=None, offset=0, clear_search=False):
    """
    Manage the search view.
    :param search_string: string to search
    :param offset: offset of the results
    :param clear_search: if true, will clear earlier searches
    :return: None
    """
    if clear_search:
        _addon.setSetting("searches", "")
    if search_string is None:
        log("Show search UI")
        listing = []
        new_search_list_item = xbmcgui.ListItem(label='[Uusi haku]')
        new_search_url = '{0}?action=new_search'.format(_url)
        listing.append((new_search_url, new_search_list_item, True))
        clear_search_list_item = xbmcgui.ListItem(label='[Tyhjennä vanhat haut]')
        clear_search_url = '{0}?action=search&clear_search=1'.format(_url)
        listing.append((clear_search_url, clear_search_list_item, True))
        searches = _addon.getSetting("searches").splitlines()
        for search_item in searches:
            search_list_item = xbmcgui.ListItem(label=search_item)
            search_url = '{0}?action=search&search_string={1}'.format(_url, search_item)
            listing.append((search_url, search_list_item, True))
        xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    else:
        result = get_json(
            "https://external.api.yle.fi/v1/programs/items.json?q={0}&offset={1}&order=publication.endtime:desc"
            "&availability=ondemand&app_id={2}&app_key={3}".format(search_string, offset, _app_id, _app_key))
        search_url = '{0}?action=search&search_string={1}&offset={2}'.format(_url, search_string, offset + 25)
        list_videos(result['data'], search_url)
    xbmcplugin.endOfDirectory(_handle)


def new_search():
    """
    Creates a new search. Saves it to add-on settings
    :return: None
    """
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText() != '':
        search_text = keyboard.getText()
        log(search_text)
        searches = _addon.getSetting("searches").splitlines()
        searches.insert(0, search_text)
        if len(searches) > 20:
            searches.pop()
        _addon.setSetting("searches", "\n".join(searches))
        search(search_text, 0)
    xbmcplugin.endOfDirectory(_handle)


def decrypt_url(encrypted_url):
    enc = base64.b64decode(encrypted_url)
    iv = enc[:16]
    cipher = AES.new(_secret_key, AES.MODE_CBC, iv)
    decrypted_url = cipher.decrypt(enc[16:])
    unpadded_url = decrypted_url[:-ord(decrypted_url[len(decrypted_url)-1:])]
    return unpadded_url


def get_json(url):
    log(url)
    response = urllib.urlopen(url)
    log(response)
    data = json.loads(response.read())
    log(data)
    return data


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
            # Display the list of videos in a provided category.
            videos = get_videos(params['category'], offset)
            url = '{0}?action=listing&category={1}&offset={2}'.format(_url, params['category'], (offset + 25))
            list_videos(videos, url)
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])
        elif params['action'] == 'search':
            search_string = None
            if 'search_string' in params:
                search_string = str(params['search_string'])
            clear_search = False
            if 'clear_search' in params:
                clear_search = bool(params['clear_search'])
            # Show search window
            search(search_string=search_string, offset=offset, clear_search=clear_search)
        elif params['action'] == 'new_search':
            # Show search window
            new_search()
        else:
            log("Unknown action: {0}".format(params['action']), xbmc.LOGERROR)
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
