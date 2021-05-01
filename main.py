# -*- coding: utf-8 -*-

import random
import sys
import urllib
import urllib.parse
import urllib.request
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

_addonid = 'plugin.video.areena'
_addon = xbmcaddon.Addon(id=_addonid)
_profile_dir = xbmcvfs.translatePath(_addon.getAddonInfo('profile'))

_yle_tv1_live_url = 'http://yletv-lh.akamaihd.net/i/yletv1hls_1@103188/master.m3u8'
_yle_tv2_live_url = 'http://yletv-lh.akamaihd.net/i/yletv2hls_1@103189/master.m3u8'
_yle_teema_fem_live_url = 'http://yletv-lh.akamaihd.net/i/yleteemafemfi_1@490775/master.m3u8'


def log(txt, log_level=xbmc.LOGDEBUG):
    """
    Log something to the kodi.log file
    :param txt: Text to write to the log
    :param log_level: Severity of the log text
    :return: None
    """
    if (_addon.getSetting("debug") == "true") or (log_level != xbmc.LOGDEBUG):
        message = u'%s: %s' % (_addonid, txt)
        xbmc.log(msg=message, level=log_level)


def live_tv_channels(path):
    url_with_resolution = get_resolution_specific_url_for_live_tv(path)
    xbmcplugin.setResolvedUrl(_handle, True, listitem=xbmcgui.ListItem(path=url_with_resolution))


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


def get_translation(translation_id):
    return _addon.getLocalizedString(translation_id)


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
        return random.choice(colors)
    if color not in colors:
        log('Unknown color "{0}."'.format(color), xbmc.LOGWARNING)
        log('Available colors: {0}'.format(colors))
        return 'black'
    return color


def show_menu():
    listing = []
    yle_1 = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(get_color('menuItemColor'), 'YLE TV1'))
    yle_1_url = '{0}?action=live&path={1}'.format(_url, _yle_tv1_live_url)
    yle_1.setProperty('IsPlayable', 'true')
    listing.append((yle_1_url, yle_1, False))
    yle_2 = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(get_color('menuItemColor'), 'YLE TV2'))
    yle_2_url = '{0}?action=live&path={1}'.format(_url, _yle_tv2_live_url)
    yle_2.setProperty('IsPlayable', 'true')
    listing.append((yle_2_url, yle_2, False))
    yle_teema_fem = xbmcgui.ListItem(
        label='[COLOR {0}]{1}[/COLOR]'.format(get_color('menuItemColor'), 'YLE TEEMA/FEM'))
    yle_teema_fem_url = '{0}?action=live&path={1}'.format(_url, _yle_teema_fem_live_url)
    yle_teema_fem.setProperty('IsPlayable', 'true')
    listing.append((yle_teema_fem_url, yle_teema_fem, False))
    open_settings_list_item = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), get_translation(32040)))
    open_settings_url = '{0}?action=settings'.format(_url)
    listing.append((open_settings_url, open_settings_list_item, True))
    warning_list_item1 = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), "YLE HAS DISABLED THE AREENA API"))
    listing.append((None, warning_list_item1, False))
    warning_list_item2 = xbmcgui.ListItem(label='[COLOR {0}]{1}[/COLOR]'.format(
        get_color('menuItemColor'), "THEREFORE THIS PLUGIN CANNOT PLAYBACK AREENA CONTENT ANYMORE"))
    listing.append((None, warning_list_item2, False))
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
    params = dict(urllib.parse.parse_qsl(param_string))
    log(params)

    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'live':
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
