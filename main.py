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
import xbmcgui
import xbmcplugin
import credentials

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

_appId = credentials._appId
_appKey = credentials._appKey
_secretKey = credentials._secretKey
_unplayableCategories = ["5-162", "5-164"]


def get_categories():
    """
    Get the list of video categories.
    Here you can insert some parsing code that retrieves
    the list of video categories (e.g. 'Movies', 'TV-shows', 'Documentaries' etc.)
    from some site or server.
    :return: list
    """
    url = "https://external.api.yle.fi/v1/programs/categories.json?app_id=" + _appId + "&app_key=" + _appKey
    response = urllib.urlopen(url)
    data = json.loads(response.read())

    #print(data['data'])

    return data['data']


def get_videos(category, offset):
    """
    Get the list of videofiles/streams.
    Here you can insert some parsing code that retrieves
    the list of videostreams in a given category from some site or server.
    :param category: str
    :return: list
    """

    url = "https://external.api.yle.fi/v1/programs/items.json?" \
          "availability=ondemand" \
          "&mediaobject=video" \
          "&category=" + category + \
          "&order=updated:desc" \
          "&contentprotection=22-0,22-1" \
          "&offset=" + str(offset) + \
          "&app_id=" + _appId + "&app_key=" + _appKey
    response = urllib.urlopen(url)
    data = json.loads(response.read())

    #print(data['data'])

    return data['data']


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    :return: None
    """
    # Get video categories
    categories = get_categories()
    # Create a list for our items.
    listing = []
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
          #list_item.setProperty('fanart_image', VIDEOS[category][0]['thumb'])
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


def list_videos(category, offset):
    """
    Create the list of playable videos in the Kodi interface.
    :param category: str
    :return: None
    """
    # Get the list of videos in the category.
    videos = get_videos(category, offset)
    # Create a list for our items.
    listing = []
    #list.append(('{0}', '...', True))
    # Iterate through videos.
    for video in videos:
        # Create a list item with a text label and a thumbnail image.
        if 'fi' in video['title']:
          list_item = xbmcgui.ListItem(label=video['title']['fi'])
        else:
          print('no finnish title for video')

        # Set a fanart image for the list item.
        # Here we use the same image as the thumbnail for simplicity's sake.
        #list_item.setProperty('fanart_image', video['thumb'])
        # Set additional info for the list item.
        #if 'fi' in video['description']:
        #  list_item.setInfo('video', {'title': video['description']['fi']})
        # Set additional graphics (banner, poster, landscape etc.) for the list item.
        # Again, here we use the same image as the thumbnail for simplicity's sake.

        if 'available' in video['image']:
          #print("Available field exists")
          if video['image']['available']:
            imageUrl = 'http://images.cdn.yle.fi/image/upload/w_240,h_240,c_fit/{0}.png'.format(video['image']['id'])
            #print("Image url is " + imageUrl)
            #list_item.setArt({'landscape': imageUrl})
            list_item.setThumbnailImage(imageUrl)
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

    list_item = xbmcgui.ListItem(label="Next page")
    url = '{0}?action=listing&category={1}&offset={2}'.format(_url, category, (offset + 25))
    listing.append((url, list_item, True))
    # Add our listing to Kodi.
    # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
    # instead of adding one by ove via addDirectoryItem.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    #xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def play_video(path):
    print(path)

    url = "https://external.api.yle.fi/v1/programs/items/" + path + ".json?app_id=" + _appId + "&app_key=" + _appKey
    response = urllib.urlopen(url)
    data = json.loads(response.read())

    for publication in data['data']['publicationEvent']:
        print publication['temporalStatus']
        if publication['temporalStatus'] == 'currently':
          print("Found correct publication, media id: " + publication['media']['id'])
          url = "https://external.api.yle.fi/v1/media/playouts.json?" \
                  "program_id=" + path + \
                  "&media_id=" + publication['media']['id'] + \
                  "&hardsubtitles=true" \
                  "&protocol=HLS&app_id=" + _appId + \
                  "&app_key=" + _appKey
          print(url)
          response = urllib.urlopen(url)
          playoutData = json.loads(response.read())
          #print(playoutData)
          encryptedUrl = playoutData['data'][0]['url']
          path = decryptUrl(encryptedUrl)

    """
    Play a video by the provided path.
    :param path: str
    :return: None
    """
    print("decrypted path: " + path)
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def decryptUrl(encryptedUrl):
    return decrypt(encryptedUrl, _secretKey)

def decrypt( enc, key ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv )
        #return cipher.decrypt( enc[16:] )
        return _unpad(cipher.decrypt( enc[16:] ))

def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring:
    :return:
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            offset = 0;
            if 'offset' in params:
              offset = int(params['offset'])
            # Display the list of videos in a provided category.
            list_videos(params['category'], offset)
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
