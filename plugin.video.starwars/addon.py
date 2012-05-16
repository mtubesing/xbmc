import urllib, re, sys
import urllib2
import math
from os.path import basename
from xml.dom.minidom import parseString
import simplejson as json
from BeautifulSoup import BeautifulSoup

# XMBC libs
import xbmc, xbmcgui, xbmcplugin, xbmcaddon


class StarWarsWeb(object):
    showarr = [
        ('The Movies', '/icons-watch-themovies.jpg ', '/watch/the-movies', '1'),   
        ('The Clone Wars', '/icons-watch-cw.jpg', '/watch/the-clone-wars', '1'),
        ('Video Games', '/icons-watch-videogames.jpg', '/watch/video-games', '0'),
        ('Behind the Scenes', '/icons-watch-bts.jpg', '/watch/behind-the-scenes', '0'),
        ('Humor', '/icons-watch-humor.jpg', '/watch/humor', '0'),
        ('Products', '/icons-watch-products.jpg', '/watch/products', '0'),
        ('Events', '/icons-watch-events.jpg', '/watch/events', '0'),  
    ]
    
    SITE_BASE = 'http://www.starwars.com'
    NAV_IMG_BASE = '/images/graphics/navigation/icons'
    VID_HOST = 'rtmpe://cp35877.edgefcs.net:1935/'
    VID_HOST_APP = 'ondemand?ovpfv=1.1'
    SWFURL = SITE_BASE + '/video/SWPlayer.swf'
    VID_INFO_URL = '?dctp=xml&template=/ftl/templates/video-xml.ftl'
        
    def __init__(self):
        pass
        
    def get_shows(self):
        shows = []
        for showname, thumb, pageroot, hascat in self.showarr:
            shows.append({'showname':showname, 
                          'showthumb':self.SITE_BASE + self.NAV_IMG_BASE + thumb,
                          'showroot':pageroot,
                          'showhascat':hascat})  
        
        return shows
    
    def get_showcategories(self, show, pageroot):
        requrl = self.SITE_BASE + pageroot
        response = urllib2.urlopen(requrl)
        link = response.read()
        response.close()
        soup = BeautifulSoup(link)
        
        cats = []
        test = soup.findAll('h4', attrs={'class' : 'title clear'})
        for i in test[1].parent.findAll('li'):
            cats.append({'caturl' : i.a['href'],
                         'catlabel': i.a['data-filter']})       
                               
        return cats
        
    
    def get_episodes(self, show, pageroot):
                
        requrl = self.SITE_BASE + pageroot
        eps = []
        
        # loop to handle multiple pages of episodes
        while requrl != '':
            response = urllib2.urlopen(requrl)
            link = response.read()
            response.close()
            soup = BeautifulSoup(link)
            
            # find next page link
            requrl = ''
            nextlink = soup.find('li', attrs={'class' : "small-next"})
            if nextlink != None:
                requrl = self.SITE_BASE + nextlink.a['href']
                        
            shows = soup.find('ul', attrs={'class' : "category-items"})('li')
            for show in shows:
                showurl = self.SITE_BASE + show.div.a['href']
                showname = show.div.a['title']
                showname2 = ''
                if show.div.p != None:
                    showname2 = show.div.p.string
                showthumb = self.SITE_BASE + show.div.div.img['src']
                if show.div.div.div != None:
                    showlen = show.div.div.div.string
                else:
                    showlen = ''
                            
                eps.append({'showurl' : showurl, 
                            'showname':showname,
                            'showname2':showname2,
                            'showthumb':showthumb,
                            'showlen':showlen})
                            
        return eps        
      

    def get_video_info(self, start_url):
        info = []
        response = urllib2.urlopen(start_url + self.VID_INFO_URL)
        data = response.read()
        response.close()
        dom = parseString(data)
        xmlnode = dom.getElementsByTagName('uri')[0]
        playpath = xmlnode.firstChild.nodeValue
        
        plot = ''
        xmlnode = dom.getElementsByTagName('summary')[0]
        if xmlnode.firstChild != None:
            plot = xmlnode.firstChild.nodeValue
        
        bgimg = ''
        xmlnode = dom.getElementsByTagName('click2play')[0]
        if xmlnode.firstChild != None:
            bgimg = self.SITE_BASE + xmlnode.firstChild.nodeValue       
            
        vid_url = self.VID_HOST + self.VID_HOST_APP + \
        ' playpath=' + playpath + ' swfUrl=' + self.SWFURL + \
        ' swfVfy=1 pageURL=' + start_url + ' app=' + self.VID_HOST_APP  
        
        info.append({'vid_url' : vid_url, 
                    'plot': plot,
                    'bgimg': bgimg})
                    
        return info
               

__addon__ = xbmcaddon.Addon(id='plugin.video.starwars')
__info__ = __addon__.getAddonInfo
__plugin__ = __info__('name')
__version__ = __info__('version')
__icon__ = __info__('icon')
__fanart__ = __info__('fanart')

PLUGIN = sys.argv[0]
HANDLE = int(sys.argv[1])
PARAMS = sys.argv[2]

class Main:
    def __init__(self, sww):
        self.sww = sww
        
        if 'action=vids' in PARAMS:
            self.videos_menu()
        elif 'action=play' in PARAMS:
            self.play_vid()
        elif 'action=vidcats' in PARAMS:
            self.videocategory_menu()
        else:
            self.shows_menu()
        
    def shows_menu(self):
        shows = sww.get_shows()
        for show in shows:
            item = xbmcgui.ListItem(label=show['showname'], thumbnailImage=show['showthumb'])  
            if show['showhascat'] == '1':
                url = '%s?action=vidcats&show=%s&pageroot=%s' % (PLUGIN, show['showname'], show['showroot'])
            else:
                url = '%s?action=vids&show=%s&pageroot=%s&ssn=-1' % (PLUGIN, show['showname'], show['showroot'])
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=True, totalItems=len(shows))
        # Sort by show name (is this necessary?)
        xbmcplugin.addSortMethod(handle=HANDLE, sortMethod=xbmcplugin.SORT_METHOD_TITLE)
        
        # End the directory
        xbmcplugin.endOfDirectory(handle=HANDLE, succeeded=True)
        
    def videocategory_menu(self):
        params = self._get_params_dict()
        show = params['show']
        pageroot = params['pageroot']
               
        categories = self.sww.get_showcategories(show, pageroot)        
        for cat in categories:
            ssn = -1
            if cat['catlabel'].startswith('Season'):
                ssn = int(cat['catlabel'][7:])
                           
            item = xbmcgui.ListItem(label=cat['catlabel'])
            url = '%s?action=vids&show=%s&pageroot=%s&ssn=%s' % (PLUGIN, show, cat['caturl'], ssn)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=True, totalItems=len(categories))
            
        # End the directory
        xbmcplugin.endOfDirectory(handle=HANDLE, succeeded=True) 
        
        
    def videos_menu(self):
        params = self._get_params_dict()
        show = params['show']
        pageroot = params['pageroot']
        ssn = params['ssn']
                
        episodes = self.sww.get_episodes(show, pageroot)        
        for ep in episodes:
            label = self._remove_html_tags(ep['showname'])
            if ep['showname2'] != '':
                label = label + '  (' + self._remove_html_tags(ep['showname2']) + ')'
            
            thumbnailref = ep['showthumb']
            item = xbmcgui.ListItem(
                label=label, 
                iconImage=thumbnailref,
                thumbnailImage=thumbnailref
            )
                        
            epval = '-1'
            s1 = ep['showname2'].rsplit('#')
            if len(s1) == 2:
                s2 = s1[1].rsplit('.')
                if len(s2) == 2:
                    epval = s2[1]            
                        
            vid_info  = self.sww.get_video_info(ep['showurl'])
            infoLabels = {'tvshowtitle': show,
                          'plot': self._remove_html_tags(vid_info[0]['plot']),
                          'episode' : int(epval),
                          'season': int(ssn),
                          'duration': ep['showlen']}
            
            item.setInfo('video', infoLabels)
            item.setProperty('fanart_image', vid_info[0]['bgimg'])                       
            params = {
                'action': 'play',
                'vid_url': urllib.quote(vid_info[0]['vid_url']),
                'show': urllib.quote(show),
                'title': urllib.quote(ep['showname'].encode('utf-8', 'ignore')),
            }            
            xbmcplugin.addDirectoryItem(
                handle=HANDLE, 
                url='%s%s' % (PLUGIN, self._params_to_string(params)), 
                listitem=item, 
                isFolder=False, 
                totalItems=len(episodes)
            )
        # set display to Confluence episode listing
        xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
        xbmc.executebuiltin("Container.SetViewMode(503)")
        
        # End the directory
        xbmcplugin.endOfDirectory(handle=HANDLE, succeeded=True)

    def play_vid(self):
        params = self._get_params_dict()        
        play_url = urllib.unquote(params['vid_url'])
        show = urllib.unquote(params['show'])
        title = urllib.unquote(params['title'])
    
        # Set video info
        listitem = xbmcgui.ListItem(show)       
        listitem.setInfo('video', {'Title': title})
        xbmc.Player( xbmc.PLAYER_CORE_MPLAYER ).play(play_url, listitem)    

    def _get_params_dict(self):
        return dict([part.split('=') for part in PARAMS[1:].split('&')])

    def _params_to_string(self, params):
        return '?%s' % ('&'.join(['%s=%s' % (k,v) for k,v in params.items()]))
    
    def _remove_html_tags(self, txt):
        p = re.compile(r'<[^<]*?/?>')        
        return p.sub('', txt)
    
if __name__ == "__main__":
    sww = StarWarsWeb()
    Main(sww)
    

    