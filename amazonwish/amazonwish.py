# Copyright (C) 2012 - Caio Begotti <caio1982@gmail.com>
# Distributed under the GPLv2, see the LICENSE file.

"""
Python version of the old and buggy Perl module WWW::Amazon::Wishlist.
It's written using LXML and XPaths for better readability. It supports the
Amazon stores in the US, UK, France, Spain, Italy, Germany, Japan and China.

You need to load the parameters of stores up before using this module:

>>> from amazonwish.config import *
"""

__author__ = "Caio Begotti <caio1982@gmail.com>"

from lxml import etree
from lxml.html import tostring, fromstring
from config import *

class Search():
    """
    The Search() class is the one to be used if you don't know an
    user's wishlist ID and need to look them up by e-mail or their name.
    
    >>> from amazonwish.amazonwish import Search
    >>> s = Search('begotti', country='us')
    """
    def _readConfig(self, country):
        params = countryParams(country)
        return params

    def __init__(self, input, country):
        params = self._readConfig(country)
        self.currency = params['currency']
        self.domain = params['domain']
        self.symbol = params['symbol']
        self.input = input
        self.country = country
        self._download()

    def _download(self):
        input = self.input
        query = ['/gp/registry/search.html?',
               'ie=UTF8',
               '&type=wishlist',
               '&field-name=',
               input]
        url = 'http://www.amazon' + self.domain + ''.join(query)

        # i thought we should use lxml's submit_form and all that stuff
        # but turns out it handles forms just fine if i can pass
        # parameters in the url query, which is good but lxml.html's
        # parse can't follow 302 amazon returns (curl's -L flag), so
        # i had to stick with etree's good and old HTMLParser
        parser = etree.HTMLParser()
        self.page = etree.parse(url, parser)
    
    def list(self):
        """
        Returns a list with tuples containing all matching usernames
        and their main wishlist ID, with which you can get secondary
        lists via the Wishlist() class.
        
        >>> lists = s.list()
        >>> for l in lists:
        >>>     print l
        """
        # before pipe, page with usernames; after, single exact matches
        names = self.page.xpath("//td/span/a//text() | //h1[@class='visitor']//text()")
        lists = self.page.xpath("//td/span/a//@href | //div[@id='sortbarDisplay']/form//@action")
        codes = []
        for l in lists:
            codes.append(l.split('/')[3])
        # FIXME: hack not to return empty search results,
        # whose only anchor text is not english
        if not 'tg' in codes:
            return zip(names, codes)


class Profile():
    """
    The Profile() class is the one responsible for retrieving
    information about a given user, such as name, profile photo,
    existing wishlists and their names and size.

    >>> from amazonwish.amazonwish import Profile
    >>> p = Profile('3MCYFXCFDH4FA', country='us')
    """

    def _readConfig(self, country):
        params = countryParams(country)
        return params

    def __init__(self, id, country):
        params = self._readConfig(country)
        self.currency = params['currency']
        self.domain = params['domain']
        self.symbol = params['symbol']
        self.id = id
        self.country = country
        self._download()

    def _download(self):
        """
        Retrieves and stores the profile page (i.e. first wishlist
        page plus user's information and other wishlists details).
        """
        domain = self.domain
        userid = self.id
        url = 'http://www.amazon' + domain + '/wishlist/' + userid
        if 'us' in self.country or 'uk' in self.country:
            parser = etree.HTMLParser(encoding='iso-latin-1')
        elif 'jp' in self.country:
            parser = etree.HTMLParser(encoding='shift-jis')
        else:
            parser = etree.HTMLParser(encoding='utf-8')
        self.page = etree.parse(url, parser)
    
    def basicInfo(self):
        """
        Returns the name of the wishlist owner and, if available,
        the address of its profile picture.

        >>> info = p.basicInfo()
        """
        # wishlists are supposed to show a first name, so it's safe to assume it will never be null
        name = self.page.xpath("//td[@id='profile-name-Field']")
        ret = []
        for s in name:
            ret.append(s.text)
        photo = self.page.xpath("//div[@id='profile']/div/img/@src")
        if photo:
            p = photo[0].split('.')
            p = '.'.join(p[:-2]) + '.' + p[-1]
            ret.append(p)
        return ret

    def wishlists(self):
        """Returns a list of wishlists codes for a given person.

        >>> lists = p.wishlists()
        """
        lists = self.page.xpath("//div[@id='profile']/div[@id='regListpublicBlock']/div/h3/a//text()")
        return lists

    def wishlistsDetails(self):
        """
        Returns a tuple with lists, the first with all wishlists
        codes and the second with their total number of items
        (i.e. wishlist size).

        >>> details = p.wishlistsDetails()
        """
        retcodes = []
        retsizes = []
        codes = self.page.xpath("//div[@id='profile']/div[@id='regListpublicBlock']/div/@id")
        for c in codes:
            retcodes.append(c.replace('regListsList',''))
        sizes = self.page.xpath("//div[@id='profile']/div[@id='regListpublicBlock']/div/div/span[1]")
        for s in sizes:
            retsizes.append(s.text)
        #TODO: i don't really know why but sometimes these guys show up empty, and only them... debug pending
        return retcodes, retsizes


class Wishlist():
    """
    The Wishlist() class is the main class of Amazon Wishlist as
    it's here where the magic happens. This class will retrieve
    through XPATH expressions the titles of all items inside a
    wishlist, their authors and co-writers, price tags, covers
    (if books) or items picture, list which external sources your
    wishlist uses and even the total amount necessary if you were
    to buy all the items at once.

    >>> from amazonwish.amazonwish import Wishlist
    >>> wl = Wishlist('3MCYFXCFDH4FA', country='us')
    """

    def _readConfig(self, country):
        params = countryParams(country)
        return params

    def __init__(self, id, country):
        params = self._readConfig(country)
        self.currency = params['currency']
        self.domain = params['domain']
        self.symbol = params['symbol']
        self.id = id
        self.country = country
        self._download()
        
    def _download(self):
        """Retrieves and stores the printable version of the wishlist for later usage."""
        domain = self.domain
        userid = self.id
        query = ['/ref=cm_wl_act_print_o?',
                 '_encoding=UTF8',
                 '&layout=standard-print',
                 '&disableNav=1',
                 '&visitor-view=1',
                 '&items-per-page=1000']
        url = 'http://www.amazon' + domain + '/wishlist/' + userid + ''.join(query)
        if 'us' in self.country or 'uk' in self.country:
            parser = etree.HTMLParser(encoding='iso-latin-1')
        elif 'jp' in self.country:
            parser = etree.HTMLParser(encoding='shift-jis')
        else:
            parser = etree.HTMLParser(encoding='utf-8')
        self.page = etree.parse(url, parser)

    def authors(self):
        """Returns the authors names and co-writers for every item.
        
        >>> authors = wl.authors()
        """
        # TODO: check .it, .ca and .de pages for misalignment, also de printing empty dups
        #       though i can't check .jp or .cn for obvious reasons...
        authors = self.page.xpath("//div[@class='pTitle']")
        attr = ('de ', 'di ', 'by ', 'von ')
        ret = []
        for a in authors:
            subtree = tostring(a, encoding='unicode', method='html', pretty_print=True)
            if 'span' in subtree:
                parser = etree.HTMLParser()
                div = etree.fromstring(subtree, parser)
                res = div.xpath("//span[@class='small itemByline']//text()")
                for a in res:
                    a = a.replace('~','').strip()
                    if a.startswith(tuple(attr)):
                        a = a[3:].strip()
                        ret.append(a)
                    else:
                        ret.append(a)
            else:
                ret.append(ur'')
        dirt = ['DVD','VHS']
        for d in dirt:
            while d in ret:
                ret.remove(d)
        return ret
    
    def titles(self):
        """
        Returns items titles, even if they are pretty long
        ones (like academic books or journals).
        
        >>> titles = wl.titles()
        """
        titles = self.page.xpath("//div[@class='pTitle']/strong//text()")
        ret = []
        for t in titles:
            ret.append(t.replace(u'\u200B', '').strip())
        return ret
    
    def prices(self):
        """Returns the price tags for every item in a wishlist.
        
        >>> prices = wl.prices()
        """
        prices = self.page.xpath("//td[@class='pPrice'][not(text()) and not(strong)] | //td[@class='pPrice']/strong[3] | //td[@class='pPrice']/strong[1]")
        ret = []
        if 'EUR' in self.currency:
            cleaner = 'EUR'
        elif 'CDN' in self.currency:
            cleaner = 'CDN' + ur'\u0024'
        elif 'GBP' in self.currency:
            cleaner = ur'\u00a3'
        else:
            cleaner = self.symbol
        for p in prices:
            res = tostring(p, encoding='unicode', method='text', pretty_print=True).strip()
            if 'At' not in res:
                # TODO: how would it work out for non-english stores? quite a huge bug ahead...
                if 'Click' in res:
                    res = ''
                ret.append(res.replace(cleaner,'').replace(',','.').replace('.00','').strip())
        return ret
    
    def via(self):
        """
        Returns the sorted original web pages from which the wished item was
        pulled, only for Universal items not from Amazon directly.
        
        >>> via = wl.via()
        """
        via = self.page.xpath("//div/form/table/tbody[*]/tr[*]/td[*]/strong[2]")
        ret = []
        for v in via:
            url = v.text.replace('www.','').replace(u'\u200B', '')
            ret.append(url.strip())
        ret = sorted(list(set(ret)))
        return ret
    
    def covers(self):
        """Returns the addresses of items pictures (e.g. book covers, albums pictures).
        
        >>> covers = wl.covers()
        """
        covers = self.page.xpath("//div/form/table/tbody[*]/tr[*]/td[*]/div[@class='pImage']/img/@src")
        ret = []
        for c in covers:
            c = c.split('.')
            c = '.'.join(c[:-2]) + '.' + c[-1]
            ret.append(c)
        return ret
   
    def urls(self):
        """Returns the page address of a given item in the wishlist, with its full details.
        
        >>> urls = wl.urls()
        """
        urls = self.page.xpath("//tbody[@class='itemWrapper']//@name")
        ret = []
        for u in urls:
            if 'item' in u:
                code = u.split('.')[3]
                if code:
                    res = 'http://www.amazon' + self.domain + '/dp/' + code
                else:
                    res = ''
                ret.append(res)
        return ret

    def ideas(self):
        """Returs a list of ideas to shop for later, as reminders
        
        >>> ideas = wl.ideas()
        """
        ret = []
        titles = self.titles()
        prices = self.prices()
        rows = zip(titles, prices)
        for r in rows:
            if "Idea" in r[1]:
                ret.append(r[0])
        return ret 

    def total_expenses(self):
        """
        Returns the total sum of all prices, without currency symbols,
        might excluse unavailable items or items without price tags.
        
        >>> total = wl.total_expenses()
        """
        tags = []
        prices = self.prices()
        for p in prices:
            if "Idea" in p:
                prices.remove(p)
        for p in filter(None, prices):
            if p.count('.') > 1:
                p = p.replace('.', '', (p.count('.') - 1))
            tags.append(float(p))
        ret = sum(tags)
        return ret
