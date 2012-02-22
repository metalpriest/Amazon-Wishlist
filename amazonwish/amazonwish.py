# -*- coding: utf-8 -*-

from config import *

from lxml import etree
from lxml.html import tostring

class Profile():
    """
    The Profile() class is the one responsible for retrieving
    information about a given user, such as name, profile photo,
    existing wishlists and their names and size.
    """

    def readConfig(self, country):
        params = countryParams(country)
        return params

    def __init__(self, id, country):
        params = self.readConfig(country)
        self.currency = params['currency']
        self.symbol = params['symbol']
        self._download(params, id)

    def _download(self, params, id):
        """Retrieves and stores the profile page (i.e. first wishlist page plus user's information and other wishlists details)."""
        domain = params['domain']
        userid = id
        url = 'http://www.amazon' + domain + '/wishlist/' + userid
        if 'GBP' in self.currency:
            parser = etree.HTMLParser(encoding='latin-1')
        else:
            parser = etree.HTMLParser(encoding='utf-8')
        self.page = etree.parse(url, parser)

    def basicInfo(self):
        """Returns the name of the wishlist owner and, if available, the address of its profile picture."""
        # wishlists are supposed to show a first name, so it's safe to assume it will never be null
        name = self.page.xpath("//td[@id='profile-name-Field']")
        ret = []
        for s in name:
            ret.append(s.text)
        photo = self.page.xpath("//div[@id='profile']/div/img/@src")
        if photo:
            ret.append(photo[0])
        return ret

    def wishlists(self):
        """Returns a list of wishlists codes for a given person."""
        lists = self.page.xpath("/html/body/div[5]/div[1]/div/div[1]/div/div[@id='profileBox']/div/div[@id='profile']/div[@id='regListpublicBlock']/div/h3/a")
        return lists

    def wishlistsDetails(self):
        """Returns a tuple with lists, the first with all wishlists codes and the second with their total number of items (i.e. wishlist size)."""
        retcodes = []
        retsizes = []
        codes = self.page.xpath("/html/body/div[5]/div[1]/div/div[1]/div/div[@id='profileBox']/div/div[@id='profile']/div[@id='regListpublicBlock']/div/@id")
        for c in codes:
            retcodes.append(c.replace('regListsList',''))
        sizes = self.page.xpath("/html/body/div[5]/div[1]/div/div[1]/div/div[@id='profileBox']/div/div[@id='profile']/div[@id='regListpublicBlock']/div/div/span[1]")
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
    """

    def readConfig(self, country):
        params = countryParams(country)
        self.currency = params['currency']
        self.symbol = params['symbol']
        return params

    def __init__(self, id, country):
        params = self.readConfig(country)
        self._download(params, id)
        
    def _download(self, params, id):
        """Retrieves and stores the printable version of the wishlist for later usage."""
        domain = params['domain']
        userid = id
        url = 'http://www.amazon' + domain + '/wishlist/' + userid + '/ref=cm_wl_act_print_o?' + '_encoding=UTF8&layout=standard-print&disableNav=1&visitor-view=1&items-per-page=1000'
        if 'GBP' in self.currency:
            parser = etree.HTMLParser(encoding='latin-1')
        else:
            parser = etree.HTMLParser(encoding='utf-8')
        self.page = etree.parse(url, parser)

    def authors(self):
        """Returns the authors names and co-writers for every item."""
        authors = self.page.xpath("/html/body/div[@id='printcfg']/div[@id='itemsTable']/div/form/table/tbody[*]/tr[1]/td[3]/div/span")
        ret = []
        for a in authors:
            ret.append(a.text)
        return ret
    
    def titles(self):
        """Returns items titles, even if they are pretty long ones (like academic books or journals)."""
        titles = self.page.xpath("/html/body/div[@id='printcfg']/div[@id='itemsTable']/div/form/table/tbody[*]/tr[*]/td[*]/div/strong")
        ret = []
        for t in titles:
            ret.append(t.text)
        return ret
    
    def prices(self):
        """Returns the price tags for every item in a wishlist."""
        prices = self.page.xpath("/html/body/div[@id='printcfg']/div[@id='itemsTable']/div/form/table/tbody[*]/tr[*]/td[@class='pPrice']/span/strong")
        ret = []
        if 'JPY' in self.currency:
            cleaner = ur'\u0081\u008f'
        elif 'EUR' in self.currency:
            cleaner = 'EUR'
        elif 'CDN' in self.currency:
            cleaner = 'CDN' + ur'\u0024'
        elif 'GBP' in self.currency:
            cleaner = ur'\u00a3'
        else:
            cleaner = self.symbol
        for p in prices:
            ret.append(p.text.replace(cleaner,'').replace(',','.').strip())
        return ret
    
    def via(self):
        """Returns the original web page from which the wished item was pulled, only for Universal items not from Amazon directly."""
        via = self.page.xpath("/html/body/div[@id='printcfg']/div[@id='itemsTable']/div/form/table/tbody[*]/tr[*]/td[*]/strong[2]")
        ret = []
        for v in via:
            ret.append(v.text.replace('www.',''))
        return ret
    
    def covers(self):
        """Returns the addresses of items pictures (e.g. book covers, albums pictures)."""
        covers = self.page.xpath("/html/body/div[@id='printcfg']/div[@id='itemsTable']/div/form/table/tbody[*]/tr[*]/td[*]/div[@class='pImage']/img/@src")
        ret = []
        for c in covers:
            ret.append(c)
        return ret
    
    def total_expenses(self):
        """Returns the total sum of all prices, without currency symbols, might excluse unavailable items or items without price tags."""
        tags = []
        for p in self.prices():
            tags.append(float(p))
        ret = sum(tags)
        return str(ret)