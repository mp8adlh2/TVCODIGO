define('selfcareRedirect', ['jquery', 'bootstrap', 'tools', 'loginTools', 'CryptoJS'], function (jquery, bootstrap, tools, loginTools, CryptoJS) {
    let redirects = {},
        user = {},
        argsCart,
        customerToken,
        infPlan,
        infCombo,
        freeDayPlan,
        freeTrialPeriodPlan,
        typePlan,
        payment_text

    acc.tools.toggleLoader(true)

    const isConnected = () => {
        if (acc.loginTools.isLoggedIn()) {
            user = JSON.parse(localStorage.getItem('user'))
            redirects = {
                ott: pageMySubscription,
                mso: sessionStorage.getItem("mobileGoToMsoSelfcareUrl") == "true" ? (user?.msoSelfcareUrl ? user.msoSelfcareUrl : '') : pageDeviceManagementMsoDth,
                midirectv: PAGE_MIDIRECTV,
                roku: rokuUrl
            }
            return true
        }
        return false
    }
    const isOTTUser = (businessUnit) => {
        return businessUnit?.toLowerCase()?.includes('ott') && (businessUnit?.toLowerCase()?.includes('br') || businessUnit?.toLowerCase()?.includes('ssla')) 
    }
    const isMSOUser = (userType, businessUnit) => {
        return userType?.toLowerCase()?.includes('mso') || businessUnit?.toLowerCase()?.includes('mso')
    }
    const _redirectSelfCareControl = () => {
        if (isOTTUser(user.businessUnit)) {
            if (acc.tools.getParameterValueByQueryString('', 'redirect')) {
                let urlRedirect = `${acc.tools.getParameterValueByQueryString('', 'redirect')}${acc.tools.getParameterValueByQueryString('', 'cupom') ? '?cupom=' + acc.tools.getParameterValueByQueryString('', 'cupom') : ''}`
                location.href = urlRedirect
            } else {
                location.href = redirects.ott
            }
        } else {
            if(localStorage.getItem('activateTv')){
                localStorage.removeItem('activateTv')
                location.href = pageActiveTV + localStorage.getItem('pinCode') 
            }else{
                if (acc.tools.getParameterValueByQueryString('', 'redirect')) {                    
                    const queryStringMso = acc.tools.getQueryStrings()
                    let urlRedirect = `${queryStringMso?.redirect}`
                    delete queryStringMso?.redirect
                    let queryStringRedirect = ''
                    for (const [key, value] of Object.entries(queryStringMso)) {
                        queryStringRedirect = acc.tools.updateQueryString(queryStringRedirect, key, value)
                    }
                    location.href = `${acc.tools.getBaseUrl()}${urlRedirect}${queryStringRedirect}`
                } else {
                    sessionStorage.getItem("mobileGoToMsoSelfcareUrl") != null && sessionStorage.removeItem("mobileGoToMsoSelfcareUrl")
                    location.href = redirects.mso
                }
            }
        }
    }

    const _redirectMidirectvControl = () => {
        if(localStorage.getItem('activateTv')){
            localStorage.removeItem('activateTv')
            location.href = pageActiveTV + localStorage.getItem('pinCode') 
        } else if (localStorage.getItem("isRokuUser") || user?.msoProvider?.toLowerCase() == 'roku'){
            localStorage.removeItem('isRokuUser')
            location.href = PAGE_ROKU
        } else {
            location.href = redirects.midirectv        
        } 
    }

    const _getPlans = async () => {
        (sessionStorage.getItem('statusAccount') == 0 && (store = userLanguage));
        let token = localStorage.getItem('sessionToken');
        return new Promise((resolve, reject) => {
            var queryPlano =
            '{ products( filter: { category_id: { eq: "' +
            id_catPlanos +
            '"} }, sort: { sort_order: DESC }) { items { name sku incompatible_products { id name sku } promotional_text button_text customAttributes (fields: ["free_trial","free_trial_period","usage_period", "terms_and_conditions", "payment_text"]) short_description { html } description { html } commercial_conditions autopromo_discount_value price_range { minimum_price { regular_price { value currency } final_price { value currency } discount { amount_off percent_off } } } small_image { position disabled url label } thumbnail { position disabled url label } ... on BundleProduct { items { uid title required type position options { uid price id position is_default label product { categories { id } incompatible_products { id name sku } id name promotional_text sku sort_order customAttributes(fields: ["free_trial","free_trial_period", "usage_period","terms_and_conditions", "type", "activation_provider"]) small_image { position disabled url label } thumbnail { position disabled url label } short_description { html } description { html } autopromo_discount_value price_range { minimum_price { regular_price { currency value } final_price { currency value } discount { amount_off percent_off __typename } } } __typename } } } } related_products { uid name promotional_text sku customAttributes(fields: ["free_trial","free_trial_period", "usage_period", "terms_and_conditions"]) button_text short_description { html } description { html } autopromo_discount_value price_range { minimum_price { regular_price { value currency } final_price { value currency } discount { amount_off percent_off } } } thumbnail { position disabled url label } } } }}';
            dtvgoService.mag("POST", queryPlano, {
                "Store": store,
            }, successGetPlans, errorGetPlans, null);
            function successGetPlans(data) {
                if (!data.errors) {
                    _successPlan(data);
                } else {
                    errorGetPlans();
                }
                resolve(data);
            }
            function errorGetPlans() {
                toggleLoader(false);
                reject(data)
            }
        })
    }
    const _successPlan = (data) => {
        let planItems = [];
        if (data.data.products.items.length > 0) {
            data.data.products.items.forEach((item) => {
                var productNamePlan = item.name;
                var typeCharge = item.customAttributes.includes("ano") ? "ano" : "mês";
                var freeTrialValue = parseInt(
                    JSON.parse(item.customAttributes).free_trial
                );
                var freeTrialPeriod = JSON.parse(item.customAttributes).free_trial_period !== false ? JSON.parse(item.customAttributes).free_trial_period.toLowerCase() : " ";
                var paymentText = JSON.parse(item.customAttributes).payment_text;
                var planType = item?.items != undefined ? JSON.parse(item.items[0].options[0].product.customAttributes).type : ''
                var termsConditions = JSON.parse(
                    item.customAttributes
                ).terms_and_conditions;
    
                planItems.push({
                    plans: [
                        {
                            name: productNamePlan,
                            items: item.items,
                            combos: item.related_products,
                            freeTrialValue: freeTrialValue,
                            freeTrialPeriod: freeTrialPeriod,
                            typeCharge: typeCharge,
                            termsConditions: termsConditions,
                            payment_text: paymentText,
                            planType
                        },
                    ],
                });
            });
            sessionStorage.setItem(
                "displayableExtras",
                JSON.stringify({ planItems })
            );
        } else {
            toggleLoader(false);
        }
    }
    
    /*
    * TCS-6614: in Buyflow 2.0 carts are only created for new accounts.
    * So for any reactivation flow starting on Buyflow 1.0, 
    * the Magento cart still needs to be created prior to redirect to the plan selection page.
    * 
    * This function creates the cart, and save it in session on success before redirecting the user to Buyflow 2.0
    */
    function createCart(token) {
        var queryCreateCart = "mutation {createEmptyCart}";

        dtvgoService.mag(
            "POST",
            queryCreateCart,
            { Authorization: token ? "Bearer " + token : undefined, Store: store },
            successCreateCart,
            errorCreateCart
        );
    }

    function successCreateCart(data) {
        if (!data.errors) {
            let cartId = data.data.createEmptyCart;
            sessionStorage.setItem('cart_id', cartId)
            location.href = pageSelectPlan
        } else {
            // How do we gracefully handle this error case in between of the two Buyflows?
            // For now, keep the same logic as in the plan selection page
            showModalErrorPlanSelection();
        }
    }

    function errorCreateCart(error) {
        // How do we gracefully handle this error case in between of the two Buyflows?
        // For now, keep the same logic as in the plan selection page
        showModalErrorPlanSelection();
    }

    function showModalErrorPlanSelection() {
        jQuery.noConflict();
        var jQueryRef = $ && typeof $.fn.modal == "function" ? $ : jQuery;
        jQueryRef("#modal-error-plan-selection").modal("show");
    }
    
    const _handleCart = (data) => {
        if (!data || data.errors) {
            throw "Error while handling shopping cart";
        }

        var hasExtra = false;

        if (data && data.data && data.data.customerCart) {
            var APIproductsList = [];
            var displayableProducts = [];
            var type = "";

            data.data.customerCart.items.forEach((item) => {
                APIproductsList.push({
                    id: item.id,
                    uid: item.uid,
                    product: {
                        name: item.product.name,
                        sku: item.product.sku,
                    },
                    quantity: 1,
                });

                if (item.product.categories.length > 0) {
                    item.product.categories.forEach((category) => {
                        if (category.name) {
                            if (
                                category.name.toLowerCase().includes("extra") ||
                                category.name.toLowerCase().includes("combo") ||
                                category.name.toLowerCase().includes("plan")
                            ) {
                                category.name.toLowerCase().includes("plan") ?
                                    (type = "plan") :
                                    (type = category.name.substring(
                                        0,
                                        category.name.length - 1
                                    ));
                            }
                        }
                    });
                }

                if (type == "plan") {
                    sessionStorage.setItem(
                        "dataPlan",
                        JSON.stringify({
                            dataProduct: item.product.name,
                        })
                    );
                }

                JSON.parse(
                    sessionStorage.getItem("displayableExtras")
                )?.planItems.forEach((product) => {
                    product.plans.forEach((plan) => {
                        if (
                             JSON.parse(sessionStorage.getItem("dataPlan")).dataProduct ==
                            plan.name
                        ) {
                            freeDayPlan = plan.freeTrialValue;
                            freeTrialPeriodPlan = plan.freeTrialPeriod;
                            typePlan = plan.typeCharge;
                            payment_text = plan.payment_text;

                            if (item.product.name.toLowerCase().includes("combo")) {
                                plan.combos.some((dado) => {
                                    if (
                                        item.product.name.replace(/ /g, "") ==
                                        dado.name.replace(/ /g, "")
                                    ) {
                                        infCombo = dado;
                                        return infCombo;
                                    }
                                });
                            } else {
                                plan.items.some((dado) => {
                                    dado.options.forEach((option) => {
                                        if (item.product.name == option.label) {
                                            infPlan = null;
                                            infPlan = option;
                                            return infPlan;
                                        }
                                    });
                                });
                            }
                        }
                    });
                });

                let productFullPrice = item.prices.price.value
                let productDiscount = item.prices?.discounts && Number(item.prices.discounts[0]?.amount?.value);
                let productFinalPrice = productDiscount > 0 && productFullPrice != productDiscount ? String(productFullPrice - productDiscount) : productFullPrice;

                displayableProducts.push({
                    id: item.id,
                    name: item.product.name,
                    sku: item.product.sku,
                    type: type,
                    price: productFinalPrice,
                    image: item.product.thumbnail.url,
                    inf: type == "Combo" ? infCombo : infPlan,
                    freeDay: type == "plan" ? freeDayPlan : "",
                    freeTrialPeriod: type == "plan" ? freeTrialPeriodPlan : "",
                    typePlan: type == "plan" ? typePlan : "",
                    payment_text: type == "plan" ? payment_text : "",
                });

                if (
                    type &&
                    (type.toLowerCase().includes("extra") ||
                        type.toLowerCase().includes("combo"))
                ) {
                    hasExtra = true;
                }
            });

            sessionStorage.setItem(
                "cart",
                JSON.stringify({
                    cart: data.data.customerCart.id,
                    APIproductsList: APIproductsList,
                    displayableProducts: displayableProducts,
                })
            );

            return {
                customerCart: data.data.customerCart,
                hasExtra: hasExtra,
                isEmptyCart: APIproductsList.length == 0,
            };
        }

        return {
            customerCart: null,
            hasExtra: null,
            isEmptyCart: null,
        };
    }

    async function isEmailVerified(customerEmail, vrioId) {
        acc.tools.toggleLoader(true);
      
        const token = getCookie("token");
        const payload = {
          data: {
            customer_email: customerEmail,
            vrio_id: vrioId
          },
        };
      
        const headers = {
          "Content-Type": "application/json",
          Authorization: "Bearer " + api_key_email_check
        };
      
        try {
          const response = await fetch(API_CHECK_EMAIL_CONFIRMATION, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(payload),
          });
      
          if (!response.ok) {
            throw new Error("Erro na requisição");
          }
      
          const result = await response.text();
          return result.trim() === "true";
        } catch (error) {
          return error;
        }
    }

    const _redirectAbandonedCart = async (flag) => {
        const customerEmail = user.userName;        
        const vrioId = user.uid;
        const redirectShop = _redirectShops();
        sessionStorage.setItem('statusAccount', 0)
        if (
            flag || 
            redirectShop ||
            argsCart.isEmptyCart == true ||
            argsCart.isEmptyCart == null
        ) {
            location.href = pageSelectPlan;
        } else if (!argsCart.isEmptyCart && !argsCart.hasExtra) {
            location.href = pageShoppingCart;
        } else if (!argsCart.isEmptyCart && argsCart.hasExtra) {
            if (localStorage.getItem('noShowEmailValidation')) {
                location.href = pageCheckout;
                return;
            }
            const isVerified = await isEmailVerified(customerEmail, vrioId);
            if(isVerified){
                localStorage.setItem('validationCodeCheck', true);
            }
            location.href = isVerified ? pageCheckout : pageEmailValidation;
        } else {
            throw "Error while redirecting with no subscription flow";
        }
    }
    const _getCart = async (token) => {
        (sessionStorage.getItem('statusAccount') == 0 && (store = userLanguage));
        return new Promise((resolve, reject) => {
            var queryGetCart =                 "{ customerCart { id items { id uid product { name sku categories { id name } thumbnail { url label } short_description { html } description { html } } prices { discounts { label amount { value } } price { value } } ... on BundleCartItem { bundle_options { values { id  uid  label  price  }  } } quantity } applied_coupons {  code } }}";
            dtvgoService.mag("POST", queryGetCart, {
                Authorization: "Bearer " + token,
                "Store": store,
            }, successGetCart, error, null);
            function successGetCart(data) {
                if (data[0]?.message && data.data?.customerCart.id) {
                    const cartId = data.data.customerCart.id;
                    clearCart(cartId, token);
                    location.href = pageSelectPlan;
                } else if(data.errors){
                    location.href = pageMySubscription;
                }
                resolve(data);
            }
            function error() {
                reject(data)
            }
        })

    }
    const _getCartStatus = async () => {
        acc.tools.toggleLoader(true);
        setTimeout(() => {
            $(() => {
                checkAbandonedPayment().then(() => {
                    acc.tools.toggleLoader(true);
                    awaitCustomerToken();            
                });
            });            
        }, 3000)
    }

    async function awaitCustomerToken(){
        customerToken = acc.tools.getCookie("token") ? acc.tools.getCookie("token") : localStorage.getItem('customerToken')
        const dataCart = await _getCart(customerToken);
        /**
         * TCS-6614: Set cart_id in session for Buyflow 2.0 usage
         */
        sessionStorage.setItem('cart_id', dataCart?.data.customerCart.id)
        argsCart = _handleCart(dataCart);
        _redirectAbandonedCart()
        
    }
    
    const _redirectShops = () => {
        let planSelect;
        let redirectShop = false;
        if (sessionStorage.getItem("cart")) {
            JSON.parse(sessionStorage.getItem("cart")).displayableProducts.forEach(
                (product) => {
                    if (product.type == "plan") {
                        planSelect = product.name;
                    }
                }
            );
        }
        if (sessionStorage.getItem("dataProduct")) {
            if (
                planSelect !=
                JSON.parse(sessionStorage.getItem("dataProduct")).dataProduct
            ) {
                redirectShop = true;
                sessionStorage.setItem(
                    "dataPlan",
                    JSON.stringify({
                        dataProduct: JSON.parse(sessionStorage.getItem("dataProduct"))
                            .dataProduct,
                    })
                );
            } else {
                redirectShop = false;
                sessionStorage.removeItem("dataProduct");
                sessionStorage.removeItem("dataOptions");
                sessionStorage.removeItem("dataSku");
                sessionStorage.removeItem("dataPricePlan");
            }
        }
        return redirectShop;
    }

    async function waitForCookie(cookieName) {
        let cookieValue;
        while (!(cookieValue = await getCookie(cookieName))) await new Promise(resolve => setTimeout(resolve, 1000));
        return cookieValue;
    };
  
  async function getCookie(cookieName) {
    try {
            const cookie = await cookieStore.get({ name: cookieName });
            return cookie?.value || null;
        } catch (error) {
            errorPlan();
            return null;
        }
    };

    const _redirectByStatus = async () => {
        if (!isMSOUser(user.userType, user.businessUnit)) {
            sessionStorage.removeItem('statusAccount');

            acc.tools.getStatusAccount().then(async status => {
                if (status == 0) {
                    let email = JSON.parse(localStorage.getItem('user')).profile.email;
                    let userGtmRegistration = {
                        "isSelfCare": false,
                        "user_email": email,
                        "hashed_user_email": CryptoJS.SHA256(email).toString(CryptoJS.enc.Base64),
                        "user_id": JSON.parse(localStorage.getItem('user')).uid
                    }
                    localStorage.setItem('userGtmRegistration', JSON.stringify(userGtmRegistration))
                    await _getPlans();
                    sessionStorage.setItem('statusAccount', 0);
                    _getCartStatus();                                                          
                }else if(status == 1){
                    sessionStorage.setItem('statusAccount', 1);

                    /**
                     * TCS-6614: for reactivation flows, legacy buyflow created the cart once the user
                     * selected a new plan in the plan selection page. 
                     * 
                     * In Buyflow 2.0 we need this cart beforehand to add stuff to it.
                     */
                    if(BUYFLOW_V2_ENABLED) {
                        waitForCookie("token").then(cookieValue => { createCart(cookieValue)})
                    } else {
                        /**
                         * TCS-6614: keep redirect to plan selection page 'as is'.
                         * For Buyflow 2.0 the variable value changes
                         */
                        location.href = pageSelectPlan
                    }
                } else if (status == 2 && localStorage.getItem('activateTv')) {
                    sessionStorage.setItem('statusAccount', 2);
                    location.href = pageActiveTV + localStorage.getItem('pinCode') 
                    localStorage.removeItem('activateTv')
                } else{
                    _redirectSelfCareControl()
                }
            })
        } else {
            localStorage.getItem('activateTv') ? location.href = pageActiveTV + localStorage.getItem('pinCode'): _redirectSelfCareControl() 
            localStorage.removeItem('activateTv')
        }
    }
    const _redirectByTypeControl = (typeRedirect) => {
        switch (typeRedirect) {
            case 'selfcare':
                return _redirectByStatus()
            case 'midirectv':
                return _redirectMidirectvControl(user)
            case 'buyflow':
                return _redirectAbandonedCart(true)
            default:
                return _redirectSelfCareControl(user)
        }
    }
    const redirectDGO = () => {
        if (isConnected()) {
            let typeRedirect
            if (user.isMiDirectv || user.businessUnit?.toLowerCase() == 'latam-ott' || user.businessUnit?.toLowerCase() == 'ssla-dth' || user.businessUnit?.toLowerCase() == 'latam-dth') {
                typeRedirect = 'midirectv'
            } else if (isOTTUser(user.businessUnit)) {
                typeRedirect = 'selfcare'
            } 
            _redirectByTypeControl(typeRedirect)
        } else {
            location.href = pageLogin
        }
    }
    redirectDGO();
}); 