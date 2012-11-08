""" XPaginate FILE """

from math import *
from django import template
from django.template import Library, Node

register = template.Library()

"""
    Django Pagination Template Tag
    Allows for complete customization on pagination display
    Renders pages a template context with the following vars avaliable
    
    total_items:        List of total pagination items
    current:            Current Page pagination is on
    per_page:           How many items per page
    has_previous:       Has links to display that go to previous pages
    has_next:           Has links to display that go fowards pages
    foward_pages:       Dictionary contaning forward page numbers
    previous_links:     Dictionary containing previous page numbers
    has_jump_previous:  Has links that "jump" backwords through previous page numbers
    has_jump_foward:    Has page numbers that "jump" through foward page numbers
    foward_page_jump:   Dictionary containg list of forward jumping page numbers
    foward_page_jump:   Dictionary containg list of previous jumping page numbers
    show_last:          Boolean that smartly determains the current page location to display a link to the last page
    show_last:          Boolean that smartly determains the current page location to display a link to the first page
"""

class XPaginate:
    def __init__(self, uri, total_items, current, per_page, show, jump, range):
        self.total_items = int(total_items)
        self.current = int(current)
        self.per_page = int(per_page)
        self.show = int(show)
        self.jump = jump
        self.range = int(range)
        self.jump_calc = 2
        self.uri = uri
        
        if self.current is 0:
            self.current = 1
        
        # Total number of pages
        self.total_pages = int(ceil(float(total_items) / float(per_page)))
        
        if self.current is not 1:
            self.has_previous = True
        else:
            self.has_previous = False
            
        if self.current < self.total_pages:
            self.has_next = True
        else:
            self.has_next = False
        
        # Get the first foward set of page links if avaliable
        self.foward_pages = []
        if self.has_next:
            a = self.current
            self.foward = int(self.current + 1)
            total = 0
            while total is not self.show:
                a = a + 1
                total = total + 1
                if a <= self.total_pages:
                    if total is self.show:
                        last_foward = a
                    self.foward_pages.append(a)
            if last_foward is self.total_pages or (last_foward + self.show) > self.total_pages:
                self.show_last = False
            else:
                self.show_last = True
            #print self.foward_pages, '\n'
        
        # GET the set of previous pages
        self.previous_pages = []
        if self.has_previous:
            self.previous = int(self.current - 1)
            a = int((self.current - 1) - self.show)
            total = 0
            while total is not self.show:
                a = a + 1
                total = total + 1
                if a <= self.total_pages and a is not 0:
                    if total is self.show:
                        last_previous = int(a)
                    self.previous_pages.append(a)
            
            #print self.previous_pages, '\n'
                    
        # Calculate if we have the ability to jump foward pages
        if self.jump and (self.current - ceil(self.range * self.jump_calc)) >= 2:
            self.has_jump_previous = True
        else:
            self.has_jump_previous = False
            
        if self.jump and (self.current + ceil(self.range * self.jump_calc)) < self.total_pages:
            self.has_jump_foward = True
        else:
            self.has_jump_foward = False
        
        ## Calc Jump pages foward
        
        if self.has_jump_foward:
            a = last_foward
            total = 0
            self.foward_page_jump = []
            while total is not self.range:
                total = total + 1
                a = int(float(ceil(a * self.jump_calc)))
                if a <= self.total_pages:
                    self.foward_page_jump.append(a)
            
        if self.has_jump_previous:
            a = int(last_previous)
            total = 0
            self.previous_page_jump = []
            while total is not self.range:
                total = total + 1
                a = int(ceil(a / float(self.jump_calc)))
                if a <= self.total_pages and a >= 2:
                    self.previous_page_jump.insert(0, a)
        
class RenderXPage(Node):
    def __init__(self, uri, total_items, current, per_page, show, jump, range):
        self.total_items = template.Variable(total_items)
        self.current = template.Variable(current)
        self.uri = template.Variable(uri)
        if not per_page:
            self.per_page = 10
        else:
            self.per_page = per_page
        if not show:
            self.show = 3
        else:
            self.show = show
        if not jump:
            self.jump = True
        else:
            self.jump = jump
        if not range:
            self.range = 3
        else:
            self.range = range

    def render(self, context):
        
        try:
            context['xpaginate'] = XPaginate(self.uri.resolve(context), self.total_items.resolve(context), self.current.resolve(context), self.per_page, self.show, self.jump, self.range)
        except:
            pass
        
        return ''

def xpaginator(parser, token):
    tokens = token.split_contents()
    return RenderXPage(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6], tokens[7])

register.tag('xpaginator', xpaginator)
