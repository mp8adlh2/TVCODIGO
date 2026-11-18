const site_version = '<SITE_VERSION>';
console.log(`%cSKY%c+ %cversion: %c${site_version}`, 'font-family: Arial;font-size:14px;color:#ff2424', 'color:#ffffff;font-size:16px', 'color:#ffff1a', 'color:#ffa64d');

var dtvgoService = {}

dtvgoService.mid = function (method, url, param, header, callback, callbackError, attr) {
    let headerParam = header != null && header
    var headers = {
        'content-type': 'application/json',
        ...headerParam
    };
    if ((store.includes("SELFCARE") && !url.includes('rebartechnology')) || (sessionStorage.getItem('statusAccount') != null && sessionStorage.getItem('statusAccount') != 0)) {
        headers['authorization'] = localStorage.getItem('sessionToken')
        headers['X-client-id'] = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')).uid : 'client-id'
        headers['X-client-version'] = `version=${site_version}`
        headers['X-environment'] = document.querySelector("body").getAttribute("data-environment");
    }

    let attribute = attr != null && attr

    let ajaxObj = {
        method: method,
        url: url,
        headers: headers,
        success: function (data) {
            callback(data);
        },
        error: function (xhr) {
            if (xhr.status == 403) {
                acc.loginTools.logoutUser()
            }
            callbackError(xhr, xhr.status);
        },
        ...attribute
    }

    if (param != null) ajaxObj['data'] = JSON.stringify(param)

    $.ajax(ajaxObj);
}

dtvgoService.mag = function (method, dataQuery, header, callback, callbackError, isUseJsonStringfy) {
    let headerParam = header != null && header
    var headers = {
        "content-type": "application/json",
        ...headerParam
    };
    let dtQuery = (isUseJsonStringfy != null && isUseJsonStringfy != undefined) ? { query: dataQuery } : JSON.stringify({ query: dataQuery });
    if (store.includes("SELFCARE")) {
        headers["store"] = store
        headers['auth'] = localStorage?.getItem('sessionToken')
    }
    return $.ajax({
        method: method,
        url: API_ENDPOINT,
        headers: headers,
        data: dtQuery,
        success: function (data, xhr) {
            callback(data, xhr.status);
        },
        error: function (xhr) {
            callbackError(xhr, xhr.status);
        }
    });
}

dtvgoService.magHome = function (method, query, callback, callbackError, isUseJsonStringfy) {
    var headers = {
        "content-type": "application/json",
        "store": store
    };

    let dtQuery = (isUseJsonStringfy != null && isUseJsonStringfy != undefined) ? { query: query } : JSON.stringify({ query: query });
    return $.ajax({
        method: method,
        url: location.origin.indexOf('.dev') > -1 ? API_ENDPOINT : API_ENDPOINT_HOME,
        headers: headers,
        data: dtQuery,
        success: function (data, xhr) {
            callback(data, xhr.status);
        },
        error: function (xhr) {
            callbackError(xhr, xhr.status);
        }
    });
}

dtvgoService.forgeRock = function (method, url, param, header, callback, callbackError, isAuthenticate) {
    let headers = null;
    let params = null;
    if (isAuthenticate) {

        if (acc.tools.newFeaturesFlags()?.FFLoginOttToolbox) {
            headers = {
                Authorization: authorization_forgot_password,
                ...header
            }
            params = JSON.stringify(param)
        } else {
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                Authorization: authorization_forgot_password,
                "Accept-API-Version": "resource=2.1",
                auth_chain: "ldapService"
            }
            params = param
        }
    } else {
        headers = header
        params = JSON.stringify(param)
    }

    $.ajax({
        method: method,
        url: url,
        headers: headers,
        data: params,
        success: function (data) {
            callback(data);
        },
        error: function (error) {
            callbackError(error);
        },
    });
}  

dtvgoService.others = function (method, url, param, header, callback, callbackError) {
    let headerParam = header != null && header
    var headers = {
        'content-type': 'application/json',
        ...headerParam
    };

    let ajaxObj = {
        method: method,
        url: url,
        headers: headers,
        success: function (data) {
            callback(data);
        },
        error: function (xhr) {
            callbackError(xhr, xhr.status);
        },
    }

    if (param != null) ajaxObj['data'] = url.includes('faq') ? param : JSON.stringify(param)

    $.ajax(ajaxObj);
}