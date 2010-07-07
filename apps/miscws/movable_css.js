window.onload = init;

var ndebug = true;
function init()
{
    nodes = document.getElementsByName("node");
    for (i=0; i<nodes.length; i++)  morph_node(nodes[i]);

    lines = document.getElementsByName("line");
    for (i=0; i<lines.length; i++)  draw_line(lines[i]);

    if(ndebug) document.getElementById("tnotes").innerHTML = "";
}

function morph_node(obj)
{
    id = obj.getAttribute('id');
    obj.className = "node";
    obj.style.left = obj.getAttribute('x');
    obj.style.top  = obj.getAttribute('y');
    obj.setAttribute("onmousedown","grab('"+id+"')");
    obj.setAttribute("onmousemove",null);
    color = obj.getAttribute('fill');
    if (color)  obj.style.backgroundColor = color;
}

function make_point(x, y, color)
{
    point = document.createElement('span');
    point.setAttribute('name',"point");
    point.setAttribute('x',x);
    point.setAttribute('y',y);
    point.className = "point";
    point.style.left = x;
    point.style.top  = y;
    // TODO redundant information for now, (x=style.left, ...)
    return point;
}

var node_width = 16;
var min_dots = 5;
var max_dist = 15;
function draw_line(obj)
{
        obj.innerHTML = ""; // TODO remove children instead?

        x1 = obj.getAttribute('x1');
        y1 = obj.getAttribute('y1');
        x2 = obj.getAttribute('x2');
        y2 = obj.getAttribute('y2');

        obj.className = "line";
        obj.style.left = parseInt(x1) + node_width/2;
        obj.style.top  = parseInt(y1) + node_width/2;

        d = Math.sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1));
        num_dots = Math.ceil(d/max_dist);
        if (num_dots < min_dots)  num_dots = min_dots;

        // TODO avoid floating point division somehow
        dx = (x2-x1)/num_dots>>0;
        dy = (y2-y1)/num_dots>>0;
        // Don't bother with endpoints
        for (j=1; j<num_dots; j++)
            obj.appendChild(make_point(dx*j, dy*j));
}

var base_x = 0
var base_y = 0
var base_x1 = 0
var base_y1 = 0
var base_x2 = 0
var base_y2 = 0
var base_xy = []
var sliding = null;
var first_grab = false;
function grab(id)
{
    var O=document.getElementById(id);
    if(id == null || id == '')  return;

    if(O.getAttribute('name') == 'link')
    {
        base_x1 = parseInt(O.getAttribute('x1'));
        base_y1 = parseInt(O.getAttribute('y1'));
        base_x2 = parseInt(O.getAttribute('x2'));
        base_y2 = parseInt(O.getAttribute('y2'));
        alert("Grabbed_link_"+id);
    }
    else if (O.getAttribute('name') == 'node')
    {
        base_xy = [parseInt(O.getAttribute('x')),
                   parseInt(O.getAttribute('y'))];
        alert("Grabbed_node_"+id+"_at_"+base_xy[0]+","+base_xy[1]);
    }
    else { return; }
    sliding = id;
    first_grab = true;
    document.documentElement.onmousemove=slide;
    document.documentElement.onmouseup=reset_drag;
}

function reset_drag(evt)
{
    evt = evt || event;
    slide(evt,true);
    document.documentElement.onmousemove = null;
    document.documentElement.onmouseup = null;
}

function slide(evt,last)
{
    id = sliding;
    if(id == null || id == '')  return;
    var o = document.getElementById(id);

    evt = evt || event;
    x = evt.clientX;
    y = evt.clientY;
    if (x<0) x = 0;
    if (y<0) y = 0;
    if (first_grab)
    {
        base_x = x;
        base_y = y;
        first_grab = false;
        linked = o.getAttribute("link").split('|');
        for (i=0; i<linked.length; i++)  hide_link(id,linked[i]);
    }

    dx = x - base_x;
    dy = y - base_y;

    alert("Sliding_"+id+"_"+dx+"_"+dy+"...");

    var type = id[0];

    // Is a Link
    if(type == 'l')
    {
        linked = val.split('|');
        parseTranslate(linked[0])
        x1 = base_x1 + dx;
        y1 = base_y1 + dy;
        x2 = base_x2 + dx;
        y2 = base_y2 + dy;
        o.setAttribute('x1',x1);
        o.setAttribute('y1',y1);
        o.setAttribute('x2',x2);
        o.setAttribute('y2',y2);
        move(linked[0],x1,y1);
        move(linked[1],x2,y2);
    }
    // Is a Node
    else
    {
        move(id,base_xy[0]+dx,base_xy[1]+dy,last);
    }
}

function get_link_by_nodes(moved,fixed)
{
    // Have to make strings in python or use parseInt here (or 2 > 10)
    // Important part is consistency, not meaning, suppose we could
    // just check in both directions, this way catches logic errors
    var link;
    if(fixed > moved)   link = 'l'+moved+'|'+fixed;
    else                link = 'l'+fixed+'|'+moved;
    return document.getElementById(link);
}

function hide_link(moved,fixed)
{
    alert("Hiding_Link_"+moved+"|"+fixed+"...");
    l = get_link_by_nodes(moved,fixed);
    if (!l) return;
    l.style.display = "none";

    n = document.getElementById(fixed);
    n.className += " related";
}

function relink(moved,fixed,x,y)
{
    alert("Relinking_Node_"+moved+"|"+fixed+"...");
    l = get_link_by_nodes(moved,fixed);
    if (!l) return;
    redraw = (fixed > moved)?("1"):("2");
    l.setAttribute("x"+redraw,x);
    l.setAttribute("y"+redraw,y);
    draw_line(l);
    l.style.display = "inline";

    n = document.getElementById(fixed);
    n.className = n.className.replace(" related","");
}

function move(id,x,y,last)
{
    alert("Sliding_Node_"+id+"_to_"+x+","+y+"...");
    o = document.getElementById(id);
    o.setAttribute("x",x);
    o.setAttribute("y",y);
    o.style.left = x+"px";
    o.style.top = y+"px";
    if(o.id == "tnotes")  return;
    if (last)
    {
        linked = o.getAttribute("link").split('|');
        for (i=0; i<linked.length; i++)  relink(id,linked[i],x,y);
    }
}

var lastTimeout = null;
var message = []
var msg_len = 3

function display_info(Obj)
{
    var d = document.getElementById("tnotes").firstChild.nodeValue;
    if(Obj == null)            return;
    else if(Obj == '')         d = '';
    else if(Obj.id[0] == 'l')  d = "location: "+ Obj.getAttribute("info");
    else                       d = "dpid: "+ macify(Obj.getAttribute("dpid"));

    if(lastTimeout != null) clearTimeout(lastTimeout);
    lastTimeout = setTimeout("display_info('');",5000);
}

function alert(text){
    if(ndebug) return; // Disabled during actual use

    if(message.length < msg_len)    {message[message.length] = text;}
    else
    {
        message[0] = message[1];
        message[1] = message[2];
        message[2] = text;
    }
    lines = message[2] + "<br>\n" + message[1] + "<br>\n" + message[0]
    document.getElementById("tnotes").innerHTML = lines;
    if(lastTimeout != null) clearTimeout(lastTimeout);
    lastTimeout = setTimeout("alert('Nothing...');",2000);
}
