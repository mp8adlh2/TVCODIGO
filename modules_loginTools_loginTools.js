define('loginTools', ['tools'], function () {

    function _isLoggedIn() {
        if (localStorage.getItem('user') && localStorage.getItem('sessionToken')) {
            if (!acc.tools.getCookie("token")) {
                let userStorageJson = JSON.parse(localStorage.getItem("user"));
                let isMSOUser = userStorageJson?.userType?.toLowerCase()?.includes('mso') || userStorageJson?.businessUnit?.toLowerCase()?.includes('mso') || userStorageJson?.businessUnit?.toLowerCase()?.includes('dth');
                !isMSOUser && _getEntitlementStatus(localStorage.getItem('sessionToken'));
            }
            return true
        } else {
            return false
        }
    }

    function _getCurrentPlan() {
        return new Promise((resolve, reject) => {
            dtvgoService.mid("GET", API_CONSUT_BILLING_PLAN_V2, null, { 'x-api-key': api_key_consult_subscription }, success, error, null);
            function success(data) {
                let products = {
                    plan: JSON.stringify(data.message[0])
                }
                products['plan'] = JSON.stringify(data.message)
                localStorage.setItem('userProducts', JSON.stringify(products))
                resolve(data)
            }
            function error(error) {
                reject(error)
            }
        })
    }

    function _getPartnerToken() {
        const params = new Proxy(new URLSearchParams(window.location.search), {
            get: (searchParams, prop) => searchParams.get(prop),
        });
        let code = params.code;
        return code
    }

    function _setLoginCookie(token) {
        localStorage.setItem("customerToken", token.customerToken)
        let expires = new Date(Date.now() + 3600 * 1000).toUTCString();
        document.cookie =
            "token=" + token.customerToken + "; expires=" + expires + "; path=/";

    }

    function _getUserAddress(uid) {
        dtvgoService.mid("GET", API_CONSULT_ACCOUNT_V2, null, null, successGetUserAddress, acc.tools.showErroHandlingModal);
        acc.tools.toggleLoader(true)
    }

    function successGetUserAddress(data) {
        if (data.message) {
            localStorage.setItem('userAddress', JSON.stringify(data.message))
        }
        else {
            acc.tools.toggleLoader(false)
            acc.tools.showErroHandlingModal(data)
        }
    }

    function _getEntitlementStatus(accessToken) {
        let payload = {
            provider: "forgerock",
            deviceID: "HCM_NO_DEVICE"
        }

        dtvgoService.mid("POST", API_AUTHORIZATION_STATUS_LOGIN_V2, payload, {
            "x-api-key": API_KEY_ENTITLEMENT_STATUS,
            "Authorization": accessToken
        }, _setLoginCookie, error, null);

        function error() {
            acc.tools.showErroHandlingModal()
        }
    }

    function _getUserPersonalData() {
        let payload = JSON.parse(localStorage.getItem('user')).profile
        payload.country = payload.iso2country
        delete payload.iso2country
        'customData' in payload ? delete payload.customData : ''
        dtvgoService.mid("GET", API_USER_INFO, null, api_key_API_USER_INFO, successGetUserPersonalData, acc.tools.showErroHandlingModal, null);
    }

    function successGetUserPersonalData(data) {
        if (data.message) {
            localStorage.setItem('userPersonalData', JSON.stringify(data.message))
        } else { acc.tools.showErroHandlingModal() }
    }


        const _getCancelationStatus = (subscription) => {
        return new Promise((resolve, reject) => {
            let cancelationStatus = sessionStorage.getItem('cancelationStatus')
            if (!cancelationStatus) {
                if (acc.tools.isOttSelfcare()) {
                    dtvgoService.mid(
                        "GET",
                        API_GET_CANCELATION_STATUS,
                        null,
                        { Authorization: "Bearer " + localStorage.getItem('customerToken'), "x-api-key": api_key_cancel_subscription},
                        successAccountCancelationStatus,
                        errorAccountCancelationStatus,
                        null,
                    );
                }
                function successAccountCancelationStatus(data) {
                    let response = data;
                    resolve(response)
                }
                function errorAccountCancelationStatus(error) {
                    if(error.responseJSON.error?.message.includes('No scheduled cancellation found')){
                        resolve(error)
                    }else if (error.responseJSON.error?.message.includes('canceled')) {
                        location.href = pagePayment
                    }else if (error.responseJSON.error?.message.includes("In Retry") || error.responseJSON.error?.message.includes("Grace Period")) {
                        console.log('in Retry')
                    } else{
                        reject(error)
                    }
                }
            } else {
                resolve(JSON.parse(cancelationStatus))
            }
        })
    }

    function _logoutUser() {
        // Constantes para persistir dados para WebPrivate
        const NOTIFICATIONS_PERMISSION = 'notificationsPermission';
        const PLAYER_LANGUAGE_PREFERENCES = 'playerLanguagePreferences';
        const DEVICE_ID = 'deviceId';
        const MODAL_GRAN_HERMANO_SHOWN_LIST = 'modalGranHermanoShownList';
        const LAST_LOGGEDIN_URL = 'lastLoggedInUrl';
        const PUBLIC_PDP_LINK = 'publicPdpLink';

        // Salvar Dados para o WebPrivate
        const notificationsPermission = JSON.parse(
            localStorage.getItem(NOTIFICATIONS_PERMISSION),
        ) || {};
        const playerLanguagePreferences = localStorage.getItem(PLAYER_LANGUAGE_PREFERENCES);
        const deviceId = localStorage.getItem(DEVICE_ID);
        const modalGranHermanoShownList = localStorage.getItem(MODAL_GRAN_HERMANO_SHOWN_LIST);
        const lastLoggedInUrl = localStorage.getItem(LAST_LOGGEDIN_URL);
        const publicPdpLink = localStorage.getItem(PUBLIC_PDP_LINK);

        // Limpeza da sessão
        sessionStorage.clear();
        localStorage.clear();

        // Salvar dados permanentes
        document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie =
            "forgerock_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";

        // Permanecer Dados para o WebPrivate
        if (notificationsPermission) { localStorage.setItem(NOTIFICATIONS_PERMISSION, JSON.stringify(notificationsPermission)); }
        if (deviceId) { localStorage.setItem(DEVICE_ID, deviceId); }
        if (modalGranHermanoShownList) { localStorage.setItem(MODAL_GRAN_HERMANO_SHOWN_LIST, modalGranHermanoShownList); }
        if (playerLanguagePreferences) { localStorage.setItem(PLAYER_LANGUAGE_PREFERENCES, playerLanguagePreferences); }
        if (publicPdpLink) { localStorage.setItem(PUBLIC_PDP_LINK, publicPdpLink); }
        if (lastLoggedInUrl) { localStorage.setItem(LAST_LOGGEDIN_URL, lastLoggedInUrl); }
        
        // Redirect pagina de login
        location.href = pageLogin
    }

    acc.loginTools = {
        getCurrentPlan: _getCurrentPlan,
        isLoggedIn: _isLoggedIn,
        setLoginCookie: _setLoginCookie,
        getUserAddress: _getUserAddress,
        getUserPersonalData: _getUserPersonalData,
        logoutUser: _logoutUser,
        getPartnerToken: _getPartnerToken,
        getEntitlementStatus: _getEntitlementStatus,
        getCancelationStatus: _getCancelationStatus,
    }

}) 