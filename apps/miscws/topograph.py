#!/usr/bin/python
# Reid Price
# Nicira Networks
# September 2008
#

# Dimensions must be 2 to make any sense (for now)
dimensions = 2
dim = xrange(dimensions)

class Topograph:
    bounds = [1000,600]
    repel = 200
    repel_cap = 20
    jitter_strength = 2
    low_pass = .1

    def __init__(self, filename="topo"):
        self.points = []
        self.links = []
        self.buffer = 10
        self.filename = filename

    def adjust(self):
        self.jitter()
        self.expand()
        self.contract()
        self.bound()

    def jitter(self):
        global dim
        p = self.points
        from random import random
        for i in xrange(len(p)):
            for d in dim:  p[i].pos[d] += self.jitter_strength*(random()-.5)

    def expand(self):
        global dim
        n = len(self.points)
        move = [[0 for d in dim] for p in xrange(n)]
        old = [[p.pos[d] for d in dim] for p in self.points]
        # Pairwise force calculations
        for i in xrange(n):
            for j in xrange(i+1,n):
                self.displace(i,j,old,move)
        for i in xrange(n):
            for d in dim:  self.points[i].pos[d] += move[i][d]
                
    def displace(self, a, b, pos, move):
        global dim
        delta = [pos[b][d]-pos[a][d] for d in dim]
        sq_dist = sum([dp**2 for dp in delta])
        effect = -min(self.repel/sq_dist, self.repel_cap)
        for d in dim:
            # Try to keep disconnects from being shoved too far
            if abs(effect*delta[d]) < self.low_pass:  continue
            move[a][d] += effect*delta[d]
            move[b][d] -= effect*delta[d]

    def contract(self):
        global dim
        n = len(self.links)
        move = [([0 for d in dim],[0 for d in dim]) for l in xrange(n)]
        old = [[[p.pos[d] for d in dim] for p in l.points] for l in self.links]
        for i in xrange(n):
            self.constrain(i,self.links[i],old,move)
        for i in xrange(n):
            for j in xrange(len(l.points)):
                for d in dim:
                    self.links[i].points[j].pos[d] += move[i][j][d]

    def constrain(self, i, link, pos, move):
        if not pos[i]: return
        delta = [pos[i][1][d]-pos[i][0][d] for d in dim]
        from math import sqrt
        dist = sqrt(sum([dp**2 for dp in delta]))
        pull_length = dist-link.length
        sign = pull_length < 0 and -1 or 1
        pull_length = abs(pull_length)
        if  pull_length < 2*link.slack:  return
        if  sign < 0:  cap = max(link.cap, pull_length/2)
        else:          cap = link.cap
        effect = sign*min(link.tension*(pull_length-link.slack),cap)
        for d in dim:
            move[i][0][d] += effect*delta[d]/dist
            move[i][1][d] -= effect*delta[d]/dist

    def bound(self):
        global dim
        n = len(self.points)
        for i in xrange(n):
            for d in dim:
                if self.points[i].pos[d] < self.buffer:
                    self.points[i].pos[d] = self.buffer 
                elif self.points[i].pos[d] > self.bounds[d] - self.buffer:
                    self.points[i].pos[d] = self.bounds[d] - self.buffer
        

    def to_html(self, timestamp=None):
        if timestamp == None:
            from time import time
            timestamp = time()
        file = self.filename + ".html"
        f = open(file,"w")
        f.write("""\
<html>
<head><title>NOX Topology</title>
<link rel="stylesheet" type="text/css" href="graphable.css" />
<script type="text/javascript" src="movable_css.js"></script>
</head>
<body>
<div id="tnotes">No Notes</div>
""")
        for i in self.links+self.points:
            f.write(i.to_html(timestamp)+"\n")
        f.write("""
</body>
</html>""")


def to_xml(tag, obj, arglist=None, content=None):
    if arglist == None:  arglist = obj.__dict__
    expanded = []
    for k in arglist:
        if type(arglist) == dict: v = arglist[k]
        else:                     v = k
        val = obj.__getattr__(v)
        if val != None:  expanded.append('%s="%s"' % (k,val))
    expanded = " ".join(expanded)
    if content != None: return "<%s %s>%s</%s>" % (tag, expanded, content, tag)
    else:               return "<%s %s />" % (tag, expanded)

class Point:
    html_arglist = {'id':'id', 'name':'html_name', 'link':'link', \
                    'x':'x', 'y':'y', 'fill':'fill'}
    fill = "gray"
    fontsize = 10
    count = 0
    dpid = '?'
    fullname = '?'
    html_name = 'node'

    def __init__(self):
        self.id = Point.count
        self.name = Point.count
        Point.count += 1

        self.last_drawn = None
        # x,y emulated with get/setattr
        self.strokewidth = 1
        self.fontsize = 10
        self.pos = [Topograph.bounds[d]/2 for d in dim]
        #from random import random
        #self.pos = [Topograph.bounds[d]*random() for d in dim]
        self.links = []

    def __getattr__(self, name):
        if   name in self.__dict__:  return self.__dict__[name]

        elif name == 'x':  return int(self.pos[0])
        elif name == 'y':  return int(self.pos[1])
        elif name == 'link': return '|'.join([str(l) for l in self.links])
        elif name in Point.__dict__: return Point.__dict__[name]
        else:               raise AttributeError, name

    def to_html(self, timestamp = 0):
        if self.last_drawn == timestamp:  return
        self.last_drawn = timestamp
        return to_xml("div",self,self.html_arglist,self.name)


class Link:
    html_arglist = {'id':'lid', 'name':'html_name', 'info':'info', \
                    'x1':'x1','y1':'y1','x2':'x2','y2':'y2'}
    length = 50 # make this vary with network size?
    slack = 5
    cap = 20
    tension = .1
    strokewidth = 1
    stroke = "gray"
    html_name = 'line'
    info = ""

    def __init__(self, src=None, dst=None, info=""):
        # x,y emulated with get/setattr
        self.last_drawn = None
        self.info = info
        if src and dst:
            assert src != dst, "Nuclear fission! Can't link to self"
            self.points = sorted([src, dst], key=lambda x: str(x.id))
            src.links.append(dst.id)
            dst.links.append(src.id)
        else:            self.points = []

    def __getattr__(self, name):
        if   name in self.__dict__:  return self.__dict__[name]

        elif name == 'x1':  return int(self.points[0].pos[0])
        elif name == 'y1':  return int(self.points[0].pos[1])
        elif name == 'x2':  return int(self.points[1].pos[0])
        elif name == 'y2':  return int(self.points[1].pos[1])
        elif name == 'lid': return "l"+str(self.points[0].id)+ \
                                   "|"+str(self.points[1].id)
        elif name in Link.__dict__: return Link.__dict__[name]
        else:               raise AttributeError, name

    def __setattr__(self, name, value):
        if name in ['x1','y1','x2','y2','lid']: assert False, "Can't set this"
        # Undecided on the indirect modification issue
        #elif name == 'x1':  self.__dict__['points'][0].pos[0] = value
        #elif name == 'y1':  self.__dict__['points'][0].pos[1] = value
        #elif name == 'x2':  self.__dict__['points'][1].pos[0] = value
        #elif name == 'y2':  self.__dict__['points'][1].pos[1] = value
        else:               self.__dict__[name] = value

    def to_html(self, timestamp = 0):
        if self.last_drawn == timestamp:  return
        self.last_drawn = timestamp
        # Need contents or <div [...] /> returned, leaving divs everywhere
        return to_xml("div",self,self.html_arglist,"&nbsp;")
