define('login', ['jquery', 'bootstrap', 'tools', 'loginTools', 'gtmTrack', 'CryptoJS'], function (jquery, bootstrap, tools, loginTools, gtmTrack, CryptoJS) {
    function renderReCaptcha() {    
        let attachDiv = document.querySelector('.forgot_password');
        if(!attachDiv) attachDiv = document.querySelector('#validation');
        const recaptchaDiv = document.createElement('div');    
        recaptchaDiv.setAttribute('id', 'recaptcha');    
        recaptchaDiv.setAttribute('class', 'g-recaptcha');    
        recaptchaDiv.setAttribute('data-sitekey', RECAPTCHA_KEY);   
        attachDiv.parentNode.insertBefore(recaptchaDiv, attachDiv);
        grecaptcha.enterprise.render('recaptcha', {        
            'sitekey': RECAPTCHA_KEY,
            'callback': recaptchaCompleted, 
            'action': 'LOGIN',
            'size': 'normal'
        });
    }

    grecaptcha.enterprise.ready(function(){
        const recaptchaContainer = document.querySelector('form.login__form');    
        if (recaptchaContainer !== null) {
            renderReCaptcha()
        }
    });

    let deviceId;
    (async () => {
        deviceId = await acc.tools.getDeviceId();
    })();

    let gtmObjLogin;
	let ga4TrackingObjectParams = {};
    const clientType = "web";
		
	$(window).ready(() => {
		ga4TrackingObjectParams = {
            'section': location.pathname.split("/").pop(),
			'v_client_id': 'not logged', 
			'v_language': 'pt',
			'v_app_name': 'skymais-web'
		}

		gtmObjLogin = $('.gtmObjLogin').attr('data-gtm-obj');
		gtmObjLogin =  gtmObjLogin && acc.gtmTrack.getObjParseGtm(gtmObjLogin);
		
		window.dataLayer.push({
            "event": "interactions",
            "eventParams": {
                'v_page_name': 'login/login-page-provider', 
			    ...ga4TrackingObjectParams, 
                'hash': gtmObjLogin?.pageView
            }
        });

		$(".forgot_password a").on("click", () => {
			window.dataLayer.push({
                "event": "interactions",
                "eventParams": {
                    'v_category': 'login:login-page-provider', 
                    'v_action': 'navigation', 
                    'v_label': 'forgot-password', 
                    ...ga4TrackingObjectParams,
                    'hash': gtmObjLogin?.forgotPassword
                }
            });
		});

		$(".mso-loggin-buttons-field .button").on("click", () => {
			window.dataLayer.push({
                "event": "interactions",
                "eventParams": {
                    'v_category': 'login:login-page-provider', 
                    'v_action': 'navigation', 
                    'v_label': 'login-provider', 
                    ...ga4TrackingObjectParams,
                    'hash': gtmObjLogin?.loginProvider
                }
            });
		});
	});
    
    /* Add condition isLoginMSOTbx */ 
    const isLoginMSOTbx = document.querySelector('#login-dgo')?.dataset?.msoTbx ? true : false; 
    acc.loginTools.getPartnerToken() ? partnerLogin(acc.loginTools.getPartnerToken(), localStorage.getItem('isSky')) : ''
    location.href.includes('activar') || location.href.includes('ativar') ? localStorage.setItem('activateTv', true) : '';
    location.href.includes('?pinCode=') ? localStorage.setItem('pinCode', location.href.split('?pinCode=')[1]?.split('&')[0]) : '';
    
    acc.loginTools.isLoggedIn() ? setRedirect() : ''
    
    localStorage.removeItem('planNonMarketed');
    let errorLogin
    
    if(localStorage.getItem("resetPassword")){
        toastr["success"](
            p_translated_resetPasswordSuccessDesc,
            p_translated_resetPasswordSuccessTitle
            );
            localStorage.removeItem('resetPassword');
        }
    function getForgeRockData(email, password, tokenRecaptcha) {

        return new Promise((resolve, reject) => {

            let payload = {
                claims: '{ "id_token": { "deviceId": { "value": ' + deviceId + '}}}',
                grant_type: "password",
                username: email,
                password: password,
                scope: "openid profile entitlements vrio device",
            }

            if (acc.tools.newFeaturesFlags()?.FFLoginOttToolbox) {
                const { grant_type, username, password } = payload
                payload = {
                    grantType: grant_type,
                    password,
                    username,
                    region: 'br',
                    "g-recaptcha-response": tokenRecaptcha,
                }
            }

            const endPointLogin = TOOLBOX_LOGIN_URL + TOOLBOX_VERSION + "/oauth2/token"

            const headerLoginToolbox = {
                "x-client-type": clientType,
                "Content-Type": "application/json",
                "x-device-id": deviceId,
                "x-app": "skymais",
			}

            dtvgoService.forgeRock("POST", endPointLogin, payload, acc.tools.newFeaturesFlags()?.FFLoginOttToolbox ? headerLoginToolbox : '', successGetForgeRock, errorGetForgeRock, true)

            function successGetForgeRock(data) {
                const userDataParseJWT = parseJwt(data.id_token)
                const saveDataRenewEntitlements = {
                    ...data,
                    expireDate: ((userDataParseJWT?.exp || data?.expires_in) * 1000),
                }
                localStorage.setItem('renewEntitlements', JSON.stringify(saveDataRenewEntitlements || data))
                localStorage.setItem('sessionToken', data.id_token)
                if (acc.tools.newFeaturesFlags()?.FFLoginOttToolbox) localStorage.setItem('isOttTbx', true)
                resolve(data)
            }

            function errorGetForgeRock(error) {
                errorLogin = true;
                reject(error)
            }
        })
    }

    $('#extraChannelsSection a').on('click', function (e) {
        e.preventDefault()
        e.stopImmediatePropagation()
        localStorage.setItem('msoSelfcareUrl', $(this).attr('data-selfcare'))
        localStorage.setItem('deviceId', deviceId)
        if ($(this).children('.nomeProveedor').text().toLowerCase().includes('sky')) {
            localStorage.setItem('isSky', true)

            let pp = new RegExp('(alpha74|www.)').test(window.location.host) ? '' : '&pp=true'

            location.href = `${$(this).attr('href')}&deviceid=${deviceId}${pp}`
        } else {
            localStorage.setItem('isSky', false)
            location.href = $(this).attr('href')
        }
    })

    // Add functions to setStorage for TBX Login MSO
    const setStorageMsoTBX = ({isSky, selfCareUrl}) => {
        if (isLoginMSOTbx) {
            localStorage.setItem('msoSelfcareUrl', selfCareUrl);
            localStorage.setItem('deviceId', deviceId);
            localStorage.setItem('isSky', isSky);
            localStorage.setItem('isMsoTbx', true);
        }else{
            localStorage.removeItem('isMsoTbx')
        }
    };

    // Add functions to redirect login for TBX Login MSO
    // When the user is SKY send to different url
    const redirectLogin = ({isSky, link}) => {
        if (!isLoginMSOTbx) return;

        const linkRedirect = encodeURIComponent(location.href) || location.href;
        const sessionStorageStore = sessionStorage.getItem('store')?.toLocaleLowerCase();

        if (isSky && (isSky === 'true' || isSky === true)) {
            const path = 'auth/authorize';
            const responseType = 'code';
            const clientId = 'dtvgo';
            const idp = 'sky_br';
            const url = `${link}${path}?client_id=${clientId}&response_type=${responseType}&redirect_uri=${linkRedirect}&idp=${idp}&country=${userLanguage}`;
            location.href = url;
        } else {
            const urlRedirect = link?.replace('{FAILURE_REDIRECT_MSO}', linkRedirect)
                    ?.replace('{SUCCESS_REDIRECT_MSO}', linkRedirect)
                    ?.replace('{COUNTRY_MSO_LOGIN}', sessionStorageStore);
            location.href = `${urlRedirect}&client_type=web`;
        }
    };

    // Add listner for click buttons TBS Login MSO
    document.addEventListener('click', (event) => {
        if (
            (event.target.classList.contains('button-partners-login') || event.target.parentElement.classList.contains('button-partners-login'))
            && isLoginMSOTbx
        ) {
            const btnObject = event.target.classList.contains('button-partners-login') ? event.target : event.target.parentElement;
            const isSky = btnObject?.dataset?.issky || false;
            const link = btnObject?.dataset?.link;
            const selfCareUrl = btnObject?.dataset?.selfcare;
            setStorageMsoTBX({isSky, selfCareUrl});
            redirectLogin({isSky, link})
        }
    });

    function partnerLogin(partnerCode, isSky) {
        const deviceIdMso = localStorage.getItem('deviceId') || 'deviceId-not-found';

        acc.tools.toggleLoader(true)
        let payload = {
            code: partnerCode
        }
        let header = {
            deviceid: deviceIdMso,
            Authorization: isLoginMSOTbx ? authorization_mso_toolbox : authorization_forgot_password,
        }

        isSky === 'true' ? header['Metadata-BusinessUnit'] = 'SKY-DTH' : header['vrio'] = 'true'

        const apiPartnerLogin = isLoginMSOTbx 
            ? TOOLBOX_LOGIN_URL + TOOLBOX_VERSION + "/oauth2/token" 
            : API_PARTNER_LOGIN;

        if (isLoginMSOTbx) {
            payload = {
                ...payload,
                "grantType": "authorizationCode"
            }
            header = {
                ...header,
                'x-client-type': clientType,
                'x-device-id': deviceIdMso,
                'x-app': 'skymais',
            }

            // Removendo duplicação deviceId no header
            delete header?.deviceid
        }

        dtvgoService.mid("POST", apiPartnerLogin, payload, header, successPartnerLogin, errorPartnerLogin, null);

        function successPartnerLogin(data) {
            let user = parseJwt(data.id_token)
            const { selfcareUrl } = user || {}
            acc.tools.toggleLoader(false)

            const userObj = {
                country: user.iso2Code,
                msoProvider: user.msoProvider,
                msoSelfcareUrl: selfcareUrl || localStorage.getItem('msoSelfcareUrl'),
                email: user?.sub,
                profile: {
                    iso2country: user.iso2Code,
                    email: user.sub,
                },
				givenName: user.givenName,
				familyName: user.familyName,
                uid: user.customerId,
                userName: user.sub,
                userType: 'mso-dth'
            }

            localStorage.removeItem('msoSelfcareUrl')

            localStorage.setItem('user', JSON.stringify(userObj))
            localStorage.setItem(
                "renewEntitlements",
                JSON.stringify({
                    expireDate: ((user?.exp || data?.expires_in) * 1000),
                    refresh_token: data.refresh_token,
                })
            );
            localStorage.setItem("sessionToken", data.id_token);
            localStorage.setItem("frToken", data.access_token);

            setRedirect()
        }
        function errorPartnerLogin(data) {

            acc.tools.toggleLoader(false)
            acc.tools.showErroHandlingModal()
        }
    }


    function parseJwt(token) {
        var base64Url = token.split(".")[1];
        var base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
        var jsonPayload = decodeURIComponent(
            atob(base64)
                .split("")
                .map(function (c) {
                    return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
                })
                .join("")
        );

        return JSON.parse(jsonPayload);
    }

    function setUserData(
        sessionToken,
        refreshToken,
        expireDate,
        forgerockId
    ) {
        const userFromOrbis = parseJwt(sessionToken);
        let type,
            midirectv = false

        if (userFromOrbis.businessUnit.toLowerCase().includes('br')) {
            type = 'ott'
        } else if (userFromOrbis.businessUnit.toLowerCase().includes('ssla') || userFromOrbis.businessUnit.toLowerCase().includes('sky-dth')) {
            type = userFromOrbis.businessUnit.toLowerCase()
        } else {
            midirectv = true
        }
        
        const userObj = {
            allowedCountry: true,
            country: userFromOrbis.iso2Code,
            isMiDirectv: midirectv,
            businessUnit: userFromOrbis.businessUnit,
            email: userFromOrbis.sub,
            iso2Code: userFromOrbis.iso2Code,
            email: userFromOrbis?.sub,
            profile: {
                iso2country: userFromOrbis.iso2Code,
                email: userFromOrbis.sub,
            },
			givenName: userFromOrbis.givenName,
			familyName: userFromOrbis.familyName,
            userName: userFromOrbis.sub,
            uid: userFromOrbis.customerId,
            userType: type
        }

		ga4TrackingObjectParams.v_client_id = userObj?.uid

		window.dataLayer.push({
            "event": "interactions",
            "eventParams": {
                'v_category': 'login:login-page-provider', 
                'v_action': 'navigation', 
                'v_label': 'sign-in', 
                ...ga4TrackingObjectParams,
                'hash': gtmObjLogin?.signIn
            }
        });

        if(userFromOrbis?.msoProvider) userObj['msoProvider'] = userFromOrbis?.msoProvider

        localStorage.setItem("user", JSON.stringify(userObj));
        localStorage.setItem(
            "renewEntitlements",
            JSON.stringify({
                expireDate: ((userFromOrbis?.exp || expireDate) * 1000),
                refresh_token: refreshToken,
            })
        );
        localStorage.setItem("sessionToken", sessionToken);
        localStorage.setItem('frToken', forgerockId)   
        setRedirect()     
    }

    async function setRedirect(){
        const queryParamSearch = window.location.search || false;
        const publicPdpUrl = localStorage.getItem('publicPdpLink') ?? null;
        const lastLoggedInUrl = localStorage.getItem('lastLoggedInUrl') ?? null;

        if (store.includes('REACTIVATION') && sessionStorage.getItem('argsCarrinho') != null) {
            location.href = pageSelectPlan + selfcare_utmParams;
        } else if (localStorage.getItem('activateTv')) {
            localStorage.removeItem('activateTv')
            const savedPinCode = localStorage.getItem('pinCode');
            localStorage.removeItem('pinCode');
            location.href = `${pageActiveTV}${savedPinCode && savedPinCode != "" ? ('?pinCode=' + savedPinCode) : ''}`;
        } else if (publicPdpUrl || lastLoggedInUrl) {
            location.href = PAGE_USER_PROFILE;
        } else if (acc.tools.mobileAndTabletCheck() == true && !store.toUpperCase().includes("SELFCARE")) {
            let user = JSON.parse(localStorage.getItem("user"));
            
            if (user?.userType?.toLowerCase()?.includes('mso') || user?.businessUnit?.toLowerCase()?.includes('mso') || user?.userType?.toLowerCase()?.includes('dth') || user?.businessUnit?.toLowerCase()?.includes('dth')) {
                location.href = PAGE_MOBILE_LOGIN;
            } else {
                await acc.tools.getStatusAccount().then(status => {
                    if (status == 0) {
                        location.href = PAGE_REDIRECT;
                    } else {
                        location.href = PAGE_MOBILE_LOGIN;
                    }
                })
            }
        } else if (location.href.includes("redirectTo")) {
            acc.tools.getParameterValueByQueryString('', 'redirectTo') ? location.href = `${PAGE_REDIRECT}?redirect=${acc.tools.getParameterValueByQueryString('', 'redirectTo')}&subjectid=${acc.tools.getParameterValueByQueryString('', 'subjectid')}&packageName=${acc.tools.getParameterValueByQueryString('', 'packageName')}` : location.href = ACTIVE_PRODUCT_URL
        } else if (acc.tools.getParameterValueByQueryString('', 'redirect')) {
            location.href = `${PAGE_REDIRECT}${queryParamSearch ? queryParamSearch : ''}`
        } else {
            location.href = ACTIVE_PRODUCT_URL
        }
    }

    async function login(user, password, tokenRecaptcha) {
        try {
            acc.tools.toggleLoader(true);
            const { id_token, refresh_token, expires_in, access_token } =
                await getForgeRockData(user, password, tokenRecaptcha);
            setUserData(id_token, refresh_token, expires_in, access_token);
        } catch (error) {
            window.dataLayer.push({
                "event": "interactions",
                "eventParams": {
                    'v_category': 'login:login-page-provider', 
                    'v_action': 'navigation', 
                    'v_label': 'sign-in', 
                    ...ga4TrackingObjectParams,
                    'hash': gtmObjLogin?.signIn
                }
            });
			
            if (errorLogin) {
                displayErrorLogin();
                acc.tools.toggleLoader(false);
                return false;
            }
            acc.loginTools.logoutUser();
            acc.tools.toggleLoader(false);
            acc.tools.showErroHandlingModal()
            return;
        } finally {
            grecaptcha.enterprise.reset();
            sessionStorage.removeItem("token-recaptcha");
        }
    }

    function displayErrorLogin(data) {
        $("#password, #email").addClass("input_error");
        $("#password").siblings(".error_message").addClass("active_error-message");
        $("#password, #email")
            .siblings(".alert_message")
            .removeClass("active_error-message");
        $("#validation").addClass("button__gray_link", "cursor").prop("disabled", true);
    }

    $("input").on("input", function () {
        var input = $(this);

        if (input.val().length) {
            input.addClass("active");
            input.siblings().addClass("labelactive");
            if (!!document.querySelector(".active_error-message")) {
                input.removeClass("input_error");
                input.siblings(".error_message").removeClass("active_error-message");
                $(this).siblings(".alert_message").removeClass("active_error-message");
            }
        } else {
            input.removeClass("active");
            input.siblings().removeClass("labelactive");
        }
    });

    function blurVerificaEmail() {
        var email = $("#email").val();
        if (email == "") {
            $(this).addClass("input_error");
            $(this).siblings(".error_message").removeClass("active_error-message");
            $(this).siblings(".alert_message").addClass("active_error-message");
            return false;
        } else {
            $(this).removeClass("input_error");
            $(this).siblings(".error_message").removeClass("active_error-message");
            $(this).siblings(".alert_message").removeClass("active_error-message");
            return true;
        }
    }
    $("#email").blur(blurVerificaEmail);

    function blurVerificaPassword() {
        var password = $("#password").val();
        if (password == "") {
            $(this).addClass("input_error");
            $(this).siblings(".error_message").removeClass("active_error-message");
            $(this).siblings(".alert_message").addClass("active_error-message");
            return false;
        } else {
            return true;
        }
    }
    $("#password").blur(blurVerificaPassword);

    const checkFormValidation = () => {
        const tokenRecap = sessionStorage.getItem("token-recaptcha");
        $('.glyphicon').css('display', 'none')
        if (blurVerificaEmail() && blurVerificaPassword() && (skipRecaptcha() || tokenRecap)) {
            $("#validation").removeClass("button__gray_link", "cursor").prop("disabled", false);
        } else if (!document.querySelector("#validation.button__gray_link")) {
            $("#validation").addClass("button__gray_link", "cursor").prop("disabled", true);
        }
    }

    $("input").keyup(checkFormValidation);

    $(".pass-view").on("click", function () {
        let passView = $(this).children("img"),
            pass = $(this).siblings("#password");

        if (passView.attr("src").includes("icon-blocked-view.svg")) {
            $(passView).attr("src", passViewOpen);
            pass.attr("type", "text");
        } else {
            $(passView).attr("src", passViewClosed);
            pass.attr("type", "password");
        }
    });

    function skipRecaptcha() {
        const urlParams = new URLSearchParams(window.location.search);
        const skipRecaptchaParam = urlParams.get('sr');
        return skipRecaptchaParam === 'true';
    }

    function isLoginPath() {
        return (location.href.includes('acessar') || location.href.includes('acceder'))
            || (location.href.includes('activar') || location.href.includes('ativar'));
    }

    function recaptchaCompleted(token) {
        sessionStorage.setItem("token-recaptcha", token);
        checkFormValidation();
    }


    function validation() {
		let email = $("#email").val();
		let password = $("#password").val();
		let hasEmail = email !== "";
		let hasPassword = password !== "";
        let tokenRecap = sessionStorage.getItem("token-recaptcha");

        function showError(selector) {
			$(selector).addClass("input_error");
			$(selector).siblings(".alert_message").addClass("active_error-message");
		}

        if (skipRecaptcha() && hasEmail && hasPassword) {
            login(email, password);
        } else if (!hasEmail || !hasPassword || !tokenRecap) {
			if (!hasEmail) showError("#email");
			if (!hasPassword) showError("#password");
            if (!tokenRecap) showError("#validation");
			return false;
		} else if (hasEmail && hasPassword && tokenRecap) {
			if (isLoginPath() && !skipRecaptcha()) {   
                login(email, password, tokenRecap);
			} else {
				login(email, password);
			}
		}
	
		return false;
	}

    $("#validation").on("click", validation);

    $(".btn_registerRedirect").click(function () {
        location.href = pageRegistration
    });
})