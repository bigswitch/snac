function redirectParent( url ) {
    //TODO: more compatible redirect
    opener.location.replace(url);
}

function redirect(url) {
    //TODO: more compatible redirect
    document.location.replace(url);
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

function lopu(form, pu_url, parent_url) {
    var puname = 'lopu';
    var win = window.open(pu_url, puname,
                          'width=306,height=200,scrollbars=no,resizable=yes');
    if (!(win.focus && win.opener) || win == null || typeof(win) == "undefined")
    {
        //alert("pu blocked:"+win.focus);
        return true;
    }
    win.opener.focus()
    win.opener.location.replace(parent_url);
    form.pu.value="1";
    form.havepu.value="1";
    form.target=puname;
    form.submit();
    return false;
}

if( typeof XMLHttpRequest == "undefined" ) {
    //TODO: Add window.onerror to handle browsers that don't suppor try/catch
    // see http://tinyurl.com/6xbjfp
    XMLHttpRequest = function() {
        try { return new ActiveXObject("Msxml2.XMLHTTP.6.0"); } catch(e) {};
        try { return new ActiveXObject("Msxml2.XMLHTTP.3.0"); } catch(e) {};
        try { return new ActiveXObject("Msxml2.XMLHTTP");     } catch(e) {};
        try { return new ActiveXObject("Microsoft.XMLHTTP");  } catch(e) {};
        throw new Error("XMLHttpRequest or XMLHTTP not supported.");
    };
}

function watchForAuth(check_url, redir_url, next_check_to) {
    var form = returnObjById("login");
    if (form == null) {
        return null;
    }

    try {
        var data = formData("login");
        var req = new XMLHttpRequest();
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
                    if (form.rurl !=null
                        && typeof(form.rurl)!="undefined"
                        && form.rurl.value != "")
                    {
                        redirect(form.rurl.value);
                    }
                    else {
                        redirect(redir_url);
                    }
                }
                else {
                    setTimeout('watchForAuth("'+check_url+'", "'+
                               redir_url+'", "'+next_check_to+'")',
                               next_check_to);
                }
            }
        };
        req.send(data);
    } catch(e) {
        //alert("exception:"+e); //XXX
        //not supported - do nothing
    }

}

function formData(formId) {
    formId=returnObjById(formId);
    if (formId == null) {
        return null;
    }
    var postStr= '';
    for (i = 0; i < formId.elements.length; i++) {
        formElem = formId.elements[i];
        switch (formElem.type) {
            case 'text':
            case 'select-one':
            case 'hidden':
            case 'password':
            case 'textarea':
                postStr += formElem.name + '=' + encodeURIComponent(formElem.value) + '&'
                    break;
        }
    }
    return postStr;
}


