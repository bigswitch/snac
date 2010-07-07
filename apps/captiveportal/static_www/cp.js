
if( typeof XMLHttpRequest == "undefined" ) {
    XMLHttpRequest = function() {
        try { return new ActiveXObject("Msxml2.XMLHTTP.6.0"); } catch(e) {};
        try { return new ActiveXObject("Msxml2.XMLHTTP.3.0"); } catch(e) {};
        try { return new ActiveXObject("Msxml2.XMLHTTP");     } catch(e) {};
        try { return new ActiveXObject("Microsoft.XMLHTTP");  } catch(e) {};
        return null;
    };
}

function returnObjById( id )
{
    if (document.getElementById)
        var returnVar = document.getElementById(id);
    else if (document.all)
        var returnVar = document.all[id];
    else if (document.layers)
        var returnVar = document.layers[id];
    return returnVar;
}

function redirect(url) {
    document.location.replace(url);
}

function redirOnTrue(check_url, check_payload, redir_url, next_check_to) {
    var req = new XMLHttpRequest();
    if (req != null) {
        req.open("POST", check_url, true);
        req.setRequestHeader("Content-Type",
                             "application/x-www-form-urlencoded");
        req.onreadystatechange = function () {
            if (req.readyState
                && req.readyState == 4
                && req.status == 200
                && req.responseText)
            {
                if (req.responseText == 1) {
                    redirect(redir_url);
                }
                else {
                    setTimeout('redirOnTrue("'+check_url+'", "'+
                               check_payload+'", "'+redir_url+
                               '", "'+next_check_to+'")', next_check_to);
                }
            }
        };
        req.send(check_payload);
    }
}

function disableLogin(theform) {
    if (document.all || document.getElementById) {
        for (i = 0; i < theform.length; i++) {
            felem = theform.elements[i];
            if (felem.type.toLowerCase() == "submit") {
                felem.disabled = true;
            }
            else if (felem.type.toLowerCase() == "text") {
                felem.readOnly = true;
            }
            else if (felem.type.toLowerCase() == "password") {
                felem.readOnly = true;
            }
        }
        msgDiv = returnObjById('loginMsg');
        if (in_progress_message != null) {
            msgDiv.innerHTML = in_progress_message;
        }
    }
    return true;
}

