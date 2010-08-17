/*
 * Copyright 2008 (C) Nicira, Inc.
 */
#include "ldap_proxy.hh"

#include <sstream>
#include <ctime>
#include <ctype.h>
#include <ldap.h>

#include <boost/algorithm/string/join.hpp>
#include <boost/bind.hpp>
#include <boost/foreach.hpp>
#include "loki/ScopeGuard.h"

#include "configuration/csimple_config.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::directory;
using namespace Loki;

static Vlog_module lg("ldap_directory_proxy");

namespace vigil {
namespace applications {
namespace directory {

/*************************
 * Configuration Options *
 *************************/
const string LD_PROP_SECTION_PREFIX("ldap_proxy;");
const string LD_URI_PROP("ldap_uri");
const string LD_VERSION_PROP("ldap_version");
const string LD_OP_TO_PROP("op_timeout_sec");
const string LD_OP_RETRY_PROP("op_retry_count");
const string LD_OP_RETRY_DELAY_PROP("retry_delay_ms");
const string LD_BASE_DN_PROP("base_dn");
const string LD_BROWSER_USER_PROP("browser_user_bind_dn");
const string LD_BROWSER_USER_PW_PROP("browser_user_bind_pw");
const string LD_UNAME_FIELD_PROP("username_field");
const string LD_USER_LOOKUP_PROP("user_lookup_filter");
const string LD_UNAME_IS_FIRST_RDN_PROP("uname_is_first_rdn");
const string LD_UID_FIELD_PROP("uid_field");
const string LD_NAME_FIELD_PROP("name_field");
const string LD_PHONE_FIELD_PROP("phone_field");
const string LD_EMAIL_FIELD_PROP("email_field");
const string LD_LOC_FIELD_PROP("loc_field");
const string LD_DESC_FIELD_PROP("desc_field");
const string LD_USER_FILTER_PROP("search_filter");
const string LD_USER_OBJ_GROUPS_ATTR_PROP("user_obj_groups_attr");
const string LD_GROUP_FILTER_PROP("group_filter");
const string LD_GROUP_BASE_DN_PROP("group_base_dn");
const string LD_UGNAME_FIELD_PROP("groupname_field");
const string LD_UGNAME_IS_FIRST_RDN_PROP("ugname_is_first_rdn");
const string LD_UGDESC_FIELD_PROP("ugroup_desc_field");
const string LD_UGMEMBER_FIELD_PROP("ugroup_member_field");
const string LD_UGSUBGROUP_FIELD_PROP("ugroup_subgroup_field");
const string LD_GROUP_POSIX_MODE_PROP("group_posix_mode");
const string LD_SEARCH_SUBTREE_PROP("search_subtree");
const string LD_USE_SSL_PROP("use_ssl");
const string LD_FOLLOW_REFERRALS_PROP("follow_referrals");
const string LD_ENABLED_AUTH_SIMPLE("enabled_auth_simple");
const string LD_ENABLED_USER("enabled_user_principal");
const string LD_ENABLED_USER_GROUP("enabled_user_principal_group");

}
}
}

/****************************************************************************/

static string
sanitize_string(string istr, bool translate_wildcards) {
    ostringstream ostr;
    /** Escape wildcards in user provided strings by escaping all non-alnum 
     *  characters.  (RFC 2254 states "Other characters ... may be escaped 
     *  using this mechanism, for example, non-printing characters.")
     */
    bool last_char_ast = false;
    BOOST_FOREACH(char ch, istr) {
        unsigned char uch = (unsigned char)ch;
        if (isalnum(uch)) {
            ostr << uch;
            last_char_ast = false;
        }
        else if (translate_wildcards) {
            switch (ch) {
                case '*':
                    // fall through
                case '?':
                    //LDAP filters don't support single character matches,
                    //so we take the generous approach
                    if (!last_char_ast) {
                        //don't add ** - some servers call it an invalid
                        //filter
                        ostr << '*';
                    }
                    last_char_ast = true;
                    break;
                default:
                    ostr << '\\' << std::hex << int(uch);
                    last_char_ast = false;
            }
        }
        else {
            ostr << '\\' << std::hex << int(uch);
        }
    }
    return ostr.str();
}

static inline timeval
get_remaining_tv(const timeval &deadline_tv) {
    timeval cur_tv;
    ::gettimeofday(&cur_tv, 0);
    if (deadline_tv > cur_tv) {
        return deadline_tv - cur_tv;
    }
    else {
        return make_timeval(0, 0);
    }
}

static inline bool
is_recoverable_error(int ldap_error) {
    if (ldap_error == LDAP_BUSY          ||
        ldap_error == LDAP_UNAVAILABLE   ||
        ldap_error == LDAP_SERVER_DOWN   ||
        ldap_error == LDAP_CONNECT_ERROR ||
        ldap_error == LDAP_OPERATIONS_ERROR)
    {
        return true;
    }
    return false;
}

/****************************************************************************/

Ldap_proxy_s::Ldap_proxy_s(configuration::Properties *props)
        : props(props), ld(NULL), needs_init(true), currently_bound_user()
{
    //NOP
}

Ldap_proxy_s::~Ldap_proxy_s() { 
    if (ld != NULL) {
        lg.dbg("Unbinding existing LDAP handle");
        ldap_unbind_ext_s(ld, NULL, NULL);
        ld = NULL;
    }
} 

static bool
is_ldaps(string uri) {
    static char ldapsuri[] = "ldaps://";
    if (uri.length() < sizeof(ldapsuri)-1) {
        return false;
    }
    for (int i = 0; i < sizeof(ldapsuri)-1; ++i) {
        if (tolower(uri[i]) != ldapsuri[i]) {
            return false;
        }
    }
    return true;
}

int
Ldap_proxy_s::init() {
    if (ld != NULL) {
        lg.dbg("Unbinding existing LDAP handle");
        ldap_unbind_ext_s(ld, NULL, NULL);
        ld = NULL;
    }
    lg.dbg("Initializing ldap with URI '%s'",
            PROP_FIRST_STR(props, LD_URI_PROP).c_str());
    currently_bound_user = "";
    int ret = ldap_initialize(&ld, PROP_FIRST_STR(props, LD_URI_PROP).c_str());
    if (ret != LDAP_SUCCESS) {
        lg.err("Failed to initialize LDAP client: %d (%s)", ret,
                ldap_err2string(ret));
        ld = NULL;
        return ret;
    }

    ret = ldap_set_option(ld, LDAP_OPT_PROTOCOL_VERSION,
            &PROP_FIRST_INT(props, LD_VERSION_PROP));
    if (ret != LDAP_OPT_SUCCESS) {
        lg.err("Failed to set LDAP client version: %d (%s)", ret,
                ldap_err2string(ret));
        ld = NULL;
        return ret;
    }

    ret = ldap_set_option(ld, LDAP_OPT_REFERRALS, 
            PROP_FIRST_INT(props, LD_FOLLOW_REFERRALS_PROP) ?
                LDAP_OPT_ON : LDAP_OPT_OFF);
    if (ret != LDAP_OPT_SUCCESS) {
        lg.err("Failed to set LDAP referrals to %s: %d (%s)",
                PROP_FIRST_INT(props, LD_FOLLOW_REFERRALS_PROP) ?
                    "enabled" : "disabled",
                ret, ldap_err2string(ret));
        ld = NULL;
        return ret;
    }
    int val = LDAP_NO_LIMIT;
    ret = ldap_set_option(ld, LDAP_OPT_SIZELIMIT, &val);
    if (ret != LDAP_OPT_SUCCESS) {
        lg.err("Failed to set search size limit: %d (%s)",
                ret, ldap_err2string(ret));
        ld = NULL;
        return ret;
    }

    // LDAP_OPT_X_TLS_ALLOW still requires validation of hostname in the
    // cert (event though this info is unauthenticated!)  Furthermore,
    // this validation only supports DNS or IPv6 names, but not IPv4!
    //int certreqopt = LDAP_OPT_X_TLS_ALLOW;
    int certreqopt = LDAP_OPT_X_TLS_NEVER;
    ret = ldap_set_option(ld, LDAP_OPT_X_TLS_REQUIRE_CERT, &certreqopt);
    if (ret != LDAP_OPT_SUCCESS) {
        lg.err("Failed to set cert requirement: %d (%s)",
                ret, ldap_err2string(ret));
        ld = NULL;
        return ret;
    }

    needs_init = false;
    lg.dbg("Initialization complete");
    return ret;
}

int
Ldap_proxy_s::simple_bind_with_deadline(const string& userdn,
        const string& password, const timeval& deadline_tv, int ntries,
        bool allow_anonymous)
{
    int ret;
    LDAPMessage *res;

    berval cred;
    char *pw = (char*)password.c_str();
    cred.bv_val = pw;
    cred.bv_len = strlen(pw);
    int msgid;

    /**Active Directory (others?) in certain (poor) configurations will
     * treat empty username or password as anonymous bind during a
     * simple bind operation.
     *
     * This can be avoided using secure bind instead of simple bind.
     */
    if (!allow_anonymous && (userdn.empty() || password.empty())) {
        lg.err("Disallowing empty DN or password in simple bind with "
               "allow_anonymous=False");
        return LDAP_INVALID_CREDENTIALS;
    }

    /**ldap_sasl_bind blocks up to the network timeout
     * (even though it claims to be ansynchronous)
     */
    timeval timeout = get_remaining_tv(deadline_tv);
    if (timeval_to_ms(timeout) == 0) {
        return LDAP_TIMEOUT;
    }
    ldap_set_option(ld, LDAP_OPT_NETWORK_TIMEOUT, &timeout);
    int rc = ldap_sasl_bind(ld, userdn.c_str(), LDAP_SASL_SIMPLE, &cred, NULL,
            NULL, &msgid);
    if (rc == -1) {
        lg.err("Failed to call bind to LDAP directory using DN '%s': %d (%s)",
                userdn.c_str(), msgid, ldap_err2string(msgid));
        ret = LDAP_CONNECT_ERROR;
    }
    else {
        //recompute timeout due to the time that ldap_sasl_bind took
        timeout = get_remaining_tv(deadline_tv);
        if (timeval_to_ms(timeout) == 0) {
            return LDAP_TIMEOUT;
        }
        rc = ldap_result(ld, msgid, 1, &timeout, &res);
        if (rc == 0) {
            ret = LDAP_TIMEOUT;
            lg.err("Timed out during bind to LDAP directory using DN '%s'",
                    userdn.c_str());
        }
        else if (rc == -1) {
            lg.err("Unexpected return code from ldap_sasl_bind: %d (%s)",
                    rc, ldap_err2string(rc));
            ret = LDAP_CONNECT_ERROR;
        }
        else {
            rc = ldap_parse_result(ld, res, &ret, NULL, NULL, NULL, NULL, 1);
            if (rc != LDAP_SUCCESS) {
                lg.err("Error parsing result of ldap_result after async bind "
                       "using DN '%s'", userdn.c_str());
                ret = rc;
            }
            else if (ret != LDAP_SUCCESS) {
                lg.err("Failed to bind to LDAP directory using DN '%s': "
                       "%d (%s)", userdn.c_str(), ret, ldap_err2string(ret));
            }
        }
    }

    if (ret == LDAP_SUCCESS) {
        currently_bound_user = userdn;
    }
    else if (ret == LDAP_INVALID_CREDENTIALS) {
        currently_bound_user = "";
    }
    else {
        init(); //always re-initialize on error
        if (is_recoverable_error(ret)) {
            if (ntries > 0) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Reissuing query due to previous error");
                return simple_bind_with_deadline(userdn, password, deadline_tv,
                        ntries-1, allow_anonymous);
            }
            else {
                lg.err("Maximum try count reached, returning with failure");
                return ret;
            }
        }
    }
    return ret;
}

int
Ldap_proxy_s::bind_as_browser_user(const timeval& deadline_tv, int ntries) 
{
    int rc;
    if (ld == NULL or needs_init) {
        rc = init();
        if (rc != LDAP_SUCCESS) {
            //init failures aren't recoverable with retry
            lg.err("Error %d (%s) in ldap init()", rc,
                    ldap_err2string(rc));
            return rc;
        }
    }

    if (PROP_FIRST_INT(props, LD_USE_SSL_PROP) 
        && !is_ldaps(PROP_FIRST_STR(props, LD_URI_PROP))
        && !ldap_tls_inplace(ld))
    {
        timeval timeout = get_remaining_tv(deadline_tv);
        if (timeval_to_ms(timeout) == 0) {
            return LDAP_TIMEOUT;
        }
        ldap_set_option(ld, LDAP_OPT_NETWORK_TIMEOUT, &timeout);
        int rc = ldap_start_tls_s(ld, NULL, NULL);
        if (rc != LDAP_SUCCESS) {
            init();
            if (is_recoverable_error(rc)) {
                if (ntries > 0) {
                    usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                    lg.err("Reissuing TLS connect due to error: %s",
                            ldap_err2string(rc));
                    return bind_as_browser_user(deadline_tv, ntries-1);
                }
                else {
                    lg.err("Maximum try count reached, returning with failure");
                    return LDAP_CONNECT_ERROR;
                }
            }
            lg.err("Failed to start TLS: %d (%s)", rc, ldap_err2string(rc));
            return LDAP_CONNECT_ERROR;
        }
    }

    if (currently_bound_user == PROP_FIRST_STR(props, LD_BROWSER_USER_PROP)) {
        return LDAP_SUCCESS;
    }
    lg.dbg("Binding as '%s'",
            PROP_FIRST_STR(props, LD_BROWSER_USER_PROP).c_str());
    rc = simple_bind_with_deadline(PROP_FIRST_STR(props, LD_BROWSER_USER_PROP),
            PROP_FIRST_STR(props, LD_BROWSER_USER_PW_PROP), deadline_tv,
            ntries, true);
    if (rc != LDAP_SUCCESS) {
        lg.err("Error %d (%s) while binding as browser user", rc,
                ldap_err2string(rc));
    }
    return rc;
}

DnToAttrMap
Ldap_proxy_s::_do_search_users(const std::string &queryfilter, 
        const timeval& deadline_tv, int ntries)
{
    ostringstream filter;
    filter << "(&(" <<PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP) << "=*)"
           << queryfilter;
    if (!PROP_FIRST_STR(props, LD_USER_FILTER_PROP).empty()) {
        filter << "(" << PROP_FIRST_STR(props, LD_USER_FILTER_PROP) << ")";
    }
    filter << ")";

    return get_attr_vals(PROP_FIRST_STR(props, LD_BASE_DN_PROP), filter.str(),
            PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP),
            PROP_FIRST_INT(props, LD_SEARCH_SUBTREE_PROP) ? 
                    LDAP_SCOPE_SUBTREE : LDAP_SCOPE_ONELEVEL,
            deadline_tv, ntries);
}

Result_callback
Ldap_proxy_s::search_users(const std::string &queryfilter, 
        const timeval& deadline_tv, int ntries, 
        const Principal_set_cb& cb, const Errback& eb)
{
    try {
        int rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, COMMUNICATION_ERROR, ldap_err2string(rc));
        }
    
        DnToAttrMap dn2attr = _do_search_users(queryfilter, deadline_tv,
                ntries);
        Principal_name_set pns;
        BOOST_FOREACH(DnToAttrMap::value_type v, dn2attr) {
            pns.insert(v.second);
        }
        return boost::bind(cb, pns);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error in search_users: %s", e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying query due to previous error");
                return search_users(queryfilter, deadline_tv, ntries-1,
                        cb, eb);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        return boost::bind(eb, e.get_directory_error(), string(e.what()));
    }
    catch (DirectoryException& e) {
        lg.err("Exception in search_users: %s", e.what());
        return boost::bind(eb, e.get_code(), string(e.what()));
    }
    catch (exception& e) {
        lg.err("Exception in search_users: %s", e.what());
        return boost::bind(eb, UNKNOWN_ERROR, string(e.what()));
    }
}

/*
 * return map of DN -> attribute value for all entries matching query
 */
DnToAttrMap
Ldap_proxy_s::get_attr_vals(const string& basedn, const string& entityfilter,
        const string& attr_name, int scope,
        const timeval& deadline_tv, int ntries)
{
    map<string, string> ret;

    lg.dbg("Searching at '%s' with filter: '%s'\n", basedn.c_str(),
            entityfilter.c_str());

    timeval timeout = get_remaining_tv(deadline_tv);
    if (timeval_to_ms(timeout) == 0) {
        throw DirectoryException(COMMUNICATION_ERROR, 
                "Search failed at '"+basedn+"' for query '"
                +entityfilter+"': " + ldap_err2string(LDAP_TIMEOUT));
    }

    LDAPMessage *search_result = NULL;
    char* attrs[] = {(char*)attr_name.c_str(), NULL};
    int rc = ldap_search_ext_s(ld, basedn.c_str(), scope,
            entityfilter.c_str(), attrs, 0, NULL, NULL, &timeout,
            LDAP_NO_LIMIT, &search_result);
    if (rc == LDAP_SIZELIMIT_EXCEEDED) {
        string s = "Size limit exceeded at '" + basedn
                + "' for query '" + entityfilter+"': " + ldap_err2string(rc);
        lg.err("%s", s.c_str());
        ldap_msgfree(search_result);
        throw DirectoryException(REMOTE_ERROR, s);
    }
    else if (rc != LDAP_SUCCESS) {
        lg.err("Attribute search failed at '%s' for query '%s': %s",
                basedn.c_str(), entityfilter.c_str(), ldap_err2string(rc));
        init();
        ldap_msgfree(search_result);
        throw LdapDirectoryException(rc,
                "Attribute search failed at '" + basedn
                + "' for query '" + entityfilter+"': " + ldap_err2string(rc));
    }

    LDAPMessage *entry; //doesn't need free
    struct berval **attrvals = NULL;
    if (ldap_count_entries(ld, search_result) == 0) {
        ldap_msgfree(search_result);
        return ret;
    }
    entry = ldap_first_entry(ld, search_result);
    while (entry != NULL) {
        char *dn = ldap_get_dn(ld, entry);
        if (dn == NULL) {
            lg.warn("Unexpected missing DN in query: '%s'",
                    entityfilter.c_str());
            ldap_memfree(dn);
            continue;
        }
        attrvals = ldap_get_values_len(ld, entry, attr_name.c_str());
        if (attrvals != NULL && ldap_count_values_len(attrvals) != 0) {
            ret[string(dn)] = string(attrvals[0]->bv_val, attrvals[0]->bv_len);
        }
        ldap_value_free_len(attrvals);
        ldap_memfree(dn);
        entry = ldap_next_entry(ld, entry);
    }
    ldap_msgfree(search_result);
    return ret;
}

string
Ldap_proxy_s::get_first_attr(LDAPMessage *entry, string key) {
    string ret;
    if (key.empty()) {
        return ret;
    }
    struct berval **attrvals = NULL;
    attrvals = ldap_get_values_len(ld, entry, key.c_str());
    if (attrvals == NULL || ldap_count_values_len(attrvals) == 0) {
        lg.dbg("Attribute '%s' not found on entry", key.c_str());
        return ret;
    }
    ret = string(attrvals[0]->bv_val, attrvals[0]->bv_len);
    ldap_value_free_len(attrvals);
    return ret;
}

string
Ldap_proxy_s::name_from_dn(const string& dn_str, const string& nameattr,
        const string& filter, bool use_first_rdn,
        const timeval& deadline_tv, int ntries) {
    string ret;
    int rc;
    if (use_first_rdn) {
        int flags = PROP_FIRST_INT(props, LD_VERSION_PROP) == 2 ?
                LDAP_DN_FORMAT_LDAPV2 : LDAP_DN_FORMAT_LDAPV3;
        flags |= LDAP_DN_PEDANTIC;
        LDAPDN dn;
        rc = ldap_str2dn(dn_str.c_str(), &dn, flags);
        if (rc != LDAP_SUCCESS) {
            throw DirectoryException(REMOTE_ERROR,
                    "Failed to parse DN '"+dn_str+"': " + ldap_err2string(rc));
        }
        if (dn && dn[0] && dn[0][0]) {
            ret = string(dn[0][0]->la_value.bv_val);
        }
        ldap_memfree(dn);
    }
    else {
        ostringstream queryfilter;
        queryfilter << "(&(" << nameattr << "=*)";
        if (!filter.empty()) {
            queryfilter << "(" << filter << ")";
        }
        queryfilter << ")";
        DnToAttrMap dn2attr = get_attr_vals(dn_str, queryfilter.str(),
                nameattr, LDAP_SCOPE_BASE, deadline_tv, ntries);
        if (dn2attr.size()) {
            ret = dn2attr.begin()->second;
        }
    }
    return ret;
}

Result_callback
Ldap_proxy_s::get_user(const std::string &username, 
        const timeval& deadline_tv, int ntries, 
        const Get_principal_cb& cb, const Errback& eb)
{
    try {
        int rc;

        rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, COMMUNICATION_ERROR, ldap_err2string(rc));
        }
        
        // Search for the user entry for username
        LDAPMessage *search_result = NULL;
        rc = get_user_entity(username, &search_result, deadline_tv, ntries);
        ScopeGuard search_result_guard = MakeGuard(ldap_msgfree, search_result);
        search_result_guard.AvoidUnusedVariableWarning();
        if (rc != LDAP_SUCCESS) {
            lg.err("Error %d (%s) while searching for user '%s'", rc,
                    ldap_err2string(rc), username.c_str());
            return boost::bind(eb, REMOTE_ERROR, ldap_err2string(rc));
        }

        if (ldap_count_entries(ld, search_result) == 0) {
            lg.dbg("No user found with username '%s'", username.c_str());
            return boost::bind(cb, UserInfo_ptr());
        }
        UserInfo_ptr ret(new UserInfo());
        LDAPMessage *user_entry; //doesn't need free
        user_entry = ldap_first_entry(ld, search_result);

        ret->name = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP));
        if (ret->name.length() == 0) {
            //how did the search find this? weird.
            string msg("Missing required username attribute '"
                       + PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP)
                       + "' in value");
            lg.err("%s", msg.c_str());
            return boost::bind(eb, REMOTE_ERROR, msg);
        }
        
        ret->user_id = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_UID_FIELD_PROP));
        ret->user_real_name = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_NAME_FIELD_PROP));
        ret->description = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_DESC_FIELD_PROP));
        ret->location = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_LOC_FIELD_PROP));
        ret->phone = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_PHONE_FIELD_PROP));
        ret->user_email = get_first_attr(user_entry,
                PROP_FIRST_STR(props, LD_EMAIL_FIELD_PROP));

        return boost::bind(cb, ret);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error in get_user: %s", e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying query due to previous error");
                return get_user(username, deadline_tv, ntries-1, cb, eb);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        return boost::bind(eb, e.get_directory_error(), string(e.what()));
    }
    catch (exception& e) {
        lg.err("Exception in get_user: %s", e.what());
        return boost::bind(eb, UNKNOWN_ERROR, string(e.what()));
    }
}

int
Ldap_proxy_s::get_entities_by_name(const string& basequery,
        const string& basedn, const string& filter, LDAPMessage **message,
        const timeval& deadline_tv, int ntries) {
    int rc;
    ostringstream searchfilter;
    searchfilter << "(&" << basequery;
    if (!filter.empty()) {
        searchfilter << "(" << filter << ")";
    }
    searchfilter << ")";
    //compute timeout
    timeval timeout = get_remaining_tv(deadline_tv);
    if (timeval_to_ms(timeout) == 0) {
        return LDAP_TIMEOUT;
    }
    lg.dbg("Getting all entities at '%s' with filter '%s'", 
            basedn.c_str(), searchfilter.str().c_str());
    rc = ldap_search_ext_s(ld, basedn.c_str(), 
            PROP_FIRST_INT(props, LD_SEARCH_SUBTREE_PROP) ? 
                    LDAP_SCOPE_SUBTREE : LDAP_SCOPE_ONELEVEL,
            searchfilter.str().c_str(), NULL, 0, NULL, NULL, &timeout,
            LDAP_NO_LIMIT, message);
    if (rc != LDAP_SUCCESS) {
        lg.err("Entity search failed at '%s' for query '%s': %s",
                basedn.c_str(), searchfilter.str().c_str(),
                ldap_err2string(rc));
        init();
        throw LdapDirectoryException(rc,
                "Entity search failed at '"+basedn+"' for query '"
                +searchfilter.str()+"': " + ldap_err2string(rc));
    }
    return rc;
}

int
Ldap_proxy_s::get_user_entity(const string& username,
        LDAPMessage **message, const timeval& deadline_tv, int ntries) {
    string escaped_name = sanitize_string(username, false);
    string lquery = PROP_FIRST_STR(props, LD_USER_LOOKUP_PROP);
    ostringstream basequery;
    if (lquery.empty()) {
        basequery << "(" << PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP)
                  << "=" << escaped_name << ")";
    }
    else {
        size_t pos = 0;
        size_t match = lquery.find("%{username}", pos);
        while (match != string::npos) {
            basequery << lquery.substr(pos, match-pos);
            basequery << escaped_name;
            pos = match + 11;
            match = lquery.find("%{username}", pos);
        }   
        basequery << lquery.substr(pos);
    }

    return get_entities_by_name(basequery.str(),
            PROP_FIRST_STR(props, LD_BASE_DN_PROP),
            PROP_FIRST_STR(props, LD_USER_FILTER_PROP),
            message, deadline_tv, ntries);
}

int
Ldap_proxy_s::get_user_group_entity(const string& usergroupname,
        LDAPMessage **message, const timeval& deadline_tv, int ntries) {
    string escaped_name = sanitize_string(usergroupname, false);
    ostringstream basequery;
    basequery << "(" << PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP)
              << "=" << escaped_name << ")";
    return get_entities_by_name(basequery.str(),
            PROP_FIRST_STR(props, LD_GROUP_BASE_DN_PROP),
            PROP_FIRST_STR(props, LD_GROUP_FILTER_PROP),
            message, deadline_tv, ntries);
}

Result_callback
Ldap_proxy_s::simple_auth(const string& username, const string& password,
        const Simple_auth_callback& auth_cb, int ntries, 
        const timeval& deadline_tv)
{
    int rc;
    AuthResult authres(AuthResult::SERVER_ERROR, username);

    try {
        rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc == LDAP_TIMEOUT) {
            authres.status = AuthResult::COMMUNICATION_TIMEOUT;
            return boost::bind(auth_cb, authres);
        }
        else if (rc != LDAP_SUCCESS) {
            return boost::bind(auth_cb, authres);
        }
        
        // Search for the user entry for username
        LDAPMessage *search_result = NULL;
        rc = get_user_entity(username, &search_result, deadline_tv, ntries);
        ScopeGuard search_result_guard = MakeGuard(ldap_msgfree, search_result);
        search_result_guard.AvoidUnusedVariableWarning();
        if (rc == LDAP_TIMEOUT) {
            authres.status = AuthResult::COMMUNICATION_TIMEOUT;
            return boost::bind(auth_cb, authres);
        }
        else if (rc != LDAP_SUCCESS) {
            lg.err("Error %d (%s) while searching for DN for user '%s'", rc,
                    ldap_err2string(rc), username.c_str());
            authres.status = AuthResult::SERVER_ERROR;
            return boost::bind(auth_cb, authres);
        }
        
        // Get the DN of the user entry
        LDAPMessage *user_entry; //doesn't need free
        char *dn = NULL;
        if (ldap_count_entries(ld, search_result) == 1) {
            user_entry = ldap_first_entry(ld, search_result);
            dn = ldap_get_dn(ld, user_entry);
        }
        else {
            if (ldap_count_entries(ld, search_result) > 1) {
                lg.err("Multiple results returned for user '%s', "
                         "cannot continue", username.c_str());
            }
            lg.warn("Authentication failed for user '%s': no such user",
                    username.c_str());
            authres.status = AuthResult::INVALID_CREDENTIALS;
            return boost::bind(auth_cb, authres);
        }
        //ldap_memfree checks for NULL
        ScopeGuard dn_guard = MakeGuard(ldap_memfree, dn);
        dn_guard.AvoidUnusedVariableWarning();

        // Attempt bind as user_dn to validate the password
        if (dn != NULL) {
            lg.dbg("Attempting to bind as DN '%s' with provided password",
                    dn);
            rc = simple_bind_with_deadline(string(dn), password, deadline_tv, 
                    ntries, false);
            if (rc == LDAP_SUCCESS) {
                authres.status = AuthResult::SUCCESS;
                authres.username = get_first_attr(user_entry,
                        PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP));
                if (authres.username.empty()) {
                    throw DirectoryException(REMOTE_ERROR,
                            "Could not obtain name of entity");
                }
                try {
                    //TODO: should check LD_ENABLED_USER_GROUP, but it's not
                    //      updated based on config right now
                    //PROP_FIRST_STR(props, LD_ENABLED_USER_GROUP) != NO_SUPPORT
                    if (PROP_FIRST_STR(props, LD_GROUP_BASE_DN_PROP).length()) 
                    {
                        authres.groups = get_groups_for_user_entry(user_entry,
                                deadline_tv, ntries);
                        // roles are not supported here for now (LDAP users
                        // can be assigned roles in built-in directory through
                        // global group membership)
                    }
                }
                catch (LdapDirectoryException& e) {
                    lg.err("Error getting groups during authentication: %s",
                            e.what());
                }
            }
            else if (rc == LDAP_INVALID_CREDENTIALS) {
                authres.status = AuthResult::INVALID_CREDENTIALS;
            }
            else if (rc == LDAP_TIMEOUT) {
                authres.status = AuthResult::COMMUNICATION_TIMEOUT;
            }
            else {
                lg.err("Error %d (%s) while attempting bind as DN '%s'", rc,
                        ldap_err2string(rc), dn);
                authres.status = AuthResult::SERVER_ERROR;
            }
        }

        lg.dbg("Returning %d (%s)", authres.status,
                authres.status_str().c_str());
        return boost::bind(auth_cb, authres);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error during simple auth: %s", e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying authentication due to previous error");
                return simple_auth(username, password, auth_cb, ntries-1,
                        deadline_tv);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        authres.status = AuthResult::SERVER_ERROR;
        return boost::bind(auth_cb, authres);
    }
    catch (exception& e) {
        lg.err("Exception in simple_auth: %s", e.what());
        authres.status = AuthResult::SERVER_ERROR;
        return boost::bind(auth_cb, authres);
    }
}

const Group_name_set
Ldap_proxy_s::get_groups_for_user_entry(LDAPMessage *user_entry,
                                   const timeval& deadline_tv, int ntries)
{
    Group_name_set ret;
    if (PROP_FIRST_STR(props, LD_USER_OBJ_GROUPS_ATTR_PROP).length()) {
        // pull groups from user object
        berval **vals = ldap_get_values_len(ld, user_entry, 
                PROP_FIRST_STR(props,
                    LD_USER_OBJ_GROUPS_ATTR_PROP).c_str());
        int grpcount = ldap_count_values_len(vals);
        for (int i = 0; i < grpcount; ++i) {
            string dn_str = string(vals[i]->bv_val, vals[i]->bv_len);
            string name = name_from_dn(dn_str,
                    PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP),
                    PROP_FIRST_STR(props, LD_GROUP_FILTER_PROP),
                    PROP_FIRST_INT(props, LD_UGNAME_IS_FIRST_RDN_PROP),
                    deadline_tv, ntries);
            if (name.length()) {
                ret.insert(name);
            }
        }
        ldap_value_free_len(vals);
    }
    else if (PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP).length()) {
        //query groups with user member
        string group_member_id;
        if (PROP_FIRST_INT(props, LD_GROUP_POSIX_MODE_PROP)) {
            string gid = get_first_attr(user_entry, "gidNumber");
            if (!gid.empty()) {
                string queryfilter = "(gidNumber=" +
                        sanitize_string(gid, false) + ")";
                DnToAttrMap dn2attr = _do_search_user_groups(queryfilter,
                        deadline_tv, ntries);
                BOOST_FOREACH(DnToAttrMap::value_type v, dn2attr) {
                    ret.insert(v.second);
                }
            }
            group_member_id = get_first_attr(user_entry, 
                    PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP));
            if (group_member_id.empty()) {
                throw DirectoryException(REMOTE_ERROR,
                        "Could not obtain name of entity");
            }
        }
        else {
            char* dn = ldap_get_dn(ld, user_entry);
            if (dn == NULL) {
                throw DirectoryException(REMOTE_ERROR,
                        "Could not obtain DN of entity");
            }
            group_member_id = dn;
            ldap_memfree(dn);
        }
        string queryfilter = "(" + PROP_FIRST_STR(props, LD_UGMEMBER_FIELD_PROP)
                             + "=" + sanitize_string(group_member_id, false)
                             + ")";
        DnToAttrMap dn2attr = _do_search_user_groups(queryfilter, deadline_tv,
                ntries);
        BOOST_FOREACH(DnToAttrMap::value_type v, dn2attr) {
            ret.insert(v.second);
        }
    }
    return ret;
}

Result_callback
Ldap_proxy_s::get_group_membership(const std::string &username,
                                   const timeval& deadline_tv, int ntries,
                                   const Group_set_cb& cb, const Errback& eb)
{
    try {
        int rc;
        rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, COMMUNICATION_ERROR, ldap_err2string(rc));
        }

        LDAPMessage *search_result = NULL;
        rc = get_user_entity(username, &search_result, deadline_tv, ntries);
        ScopeGuard search_result_guard = MakeGuard(ldap_msgfree, search_result);
        search_result_guard.AvoidUnusedVariableWarning();
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, REMOTE_ERROR, ldap_err2string(rc));
        }
        
        int count = ldap_count_entries(ld, search_result);
        if (count == 0) {
            lg.info("No groups to return for user '%s': no such user",
                    username.c_str());
            return boost::bind(cb, Group_name_set());
        }
        else if (count > 1) {
            string msg("Multiple results returned for user '" + username
                       + "', cannot continue");
            lg.warn("%s", msg.c_str());
            return boost::bind(eb, REMOTE_ERROR, msg);
        }

        LDAPMessage *user_entry; //doesn't need free
        user_entry = ldap_first_entry(ld, search_result);

        Group_name_set gs = get_groups_for_user_entry(user_entry, deadline_tv,
                ntries);
        return boost::bind(cb, gs);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error in get_group_membership: %s", e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying query due to previous error");
                return get_group_membership(username, deadline_tv, ntries-1,
                        cb, eb);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        return boost::bind(eb, e.get_directory_error(), string(e.what()));
    }
    catch (exception& e) {
        lg.err("Exception in get_group_membership: %s", e.what());
        return boost::bind(eb, UNKNOWN_ERROR, string(e.what()));
    }
}

DnToAttrMap
Ldap_proxy_s::_do_search_user_groups(const std::string &queryfilter, 
        const timeval& deadline_tv, int ntries)
{
    ostringstream filter;
    filter << "(&(" <<PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP) << "=*)"
           << queryfilter;
    if (!PROP_FIRST_STR(props, LD_GROUP_FILTER_PROP).empty()) {
        filter << "(" << PROP_FIRST_STR(props, LD_GROUP_FILTER_PROP) << ")";
    }
    filter << ")";

    return get_attr_vals(PROP_FIRST_STR(props, LD_GROUP_BASE_DN_PROP),
            filter.str(), PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP),
            PROP_FIRST_INT(props, LD_SEARCH_SUBTREE_PROP) ? 
                    LDAP_SCOPE_SUBTREE : LDAP_SCOPE_ONELEVEL,
            deadline_tv, ntries);
}

Result_callback
Ldap_proxy_s::search_user_groups(const std::string &queryfilter, 
        const timeval& deadline_tv, int ntries, 
        const Group_set_cb& cb, const Errback& eb)
{
    try {
        int rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, COMMUNICATION_ERROR, ldap_err2string(rc));
        }

        DnToAttrMap dn2attr = _do_search_user_groups(queryfilter, deadline_tv,
                ntries);
        Group_name_set gns;
        BOOST_FOREACH(DnToAttrMap::value_type v, dn2attr) {
            gns.insert(v.second);
        }
        return boost::bind(cb, gns);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error in search_user_groups: %d %s", e.get_code(), e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying query due to previous error");
                return search_user_groups(queryfilter, deadline_tv, ntries-1,
                        cb, eb);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        return boost::bind(eb, e.get_directory_error(), string(e.what()));
    }
    catch (exception& e) {
        lg.err("Exception in search_user_groups: %s", e.what());
        return boost::bind(eb, UNKNOWN_ERROR, string(e.what()));
    }
}

Result_callback
Ldap_proxy_s::get_group_parents(const std::string &groupname, 
        const timeval& deadline_tv, int ntries, 
        const Group_set_cb& cb, const Errback& eb)
{
    try {
        Group_name_set gns;

        if (PROP_FIRST_STR(props, LD_UGSUBGROUP_FIELD_PROP).empty()) {
            return boost::bind(cb, gns);
        }

        int rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, COMMUNICATION_ERROR, ldap_err2string(rc));
        }
        
        LDAPMessage *search_result = NULL;
        rc = get_user_group_entity(groupname, &search_result,
                deadline_tv, ntries);
        ScopeGuard search_result_guard = MakeGuard(ldap_msgfree, search_result);
        search_result_guard.AvoidUnusedVariableWarning();
        if (rc != LDAP_SUCCESS) {
            ostringstream msg;
            msg << "Remote server returned error " << rc << " ("
                << ldap_err2string(rc) << ") while searching for user group '"
                << groupname << "'";
            lg.err("%s", msg.str().c_str());
            return boost::bind(eb, REMOTE_ERROR, msg.str());
        }

        if (ldap_count_entries(ld, search_result) == 0) {
            lg.dbg("No user group found with group name '%s'",
                    groupname.c_str());
            return boost::bind(cb, gns);
        }

        LDAPMessage *group_entry; //doesn't need free
        group_entry = ldap_first_entry(ld, search_result);
        char* dn = ldap_get_dn(ld, group_entry);
        if (dn == NULL) {
            string msg("Remote server failed to return DN for user group '"
                       + groupname + "': " + ldap_err2string(rc));
            lg.err("%s", msg.c_str());
            return boost::bind(eb, REMOTE_ERROR, msg);
        }
        string dn_str = sanitize_string(dn, false);
        ldap_memfree(dn);

        string queryfilter = 
                "(" + PROP_FIRST_STR(props, LD_UGSUBGROUP_FIELD_PROP) + "="
                + dn_str + ")";
        DnToAttrMap dn2attr = _do_search_user_groups(queryfilter, deadline_tv,
                ntries);
        BOOST_FOREACH(DnToAttrMap::value_type v, dn2attr) {
            gns.insert(v.second);
        }

        return boost::bind(cb, gns);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error in get_group_parents: %s", e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying query due to previous error");
                return get_group_parents(groupname, deadline_tv, ntries-1,
                        cb, eb);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        return boost::bind(eb, e.get_directory_error(), string(e.what()));
    }
    catch (exception& e) {
        lg.err("Exception in get_group_parents: %s", e.what());
        return boost::bind(eb, UNKNOWN_ERROR, string(e.what()));
    }
}

Result_callback
Ldap_proxy_s::get_user_group(const std::string &groupname, 
        const timeval& deadline_tv, int ntries, 
        const Get_group_cb& cb, const Errback& eb)
{
    try {
        int rc;

        rc = bind_as_browser_user(deadline_tv, ntries);
        if (rc != LDAP_SUCCESS) {
            return boost::bind(eb, COMMUNICATION_ERROR, ldap_err2string(rc));
        }
        
        LDAPMessage *search_result = NULL;
        rc = get_user_group_entity(groupname, &search_result,
                deadline_tv, ntries);
        ScopeGuard search_result_guard = MakeGuard(ldap_msgfree, search_result);
        search_result_guard.AvoidUnusedVariableWarning();
        if (rc != LDAP_SUCCESS) {
            ostringstream msg;
            msg << "Remote server returned error " << rc << " ("
                << ldap_err2string(rc) << ") while searching for user "
                << "group '" << groupname << "'";
            lg.err("%s", msg.str().c_str());
            return boost::bind(eb, REMOTE_ERROR, msg.str());
        }

        if (ldap_count_entries(ld, search_result) == 0) {
            lg.dbg("No user group found with group name '%s'",
                    groupname.c_str());
            return boost::bind(cb, GroupInfo_ptr());
        }

        GroupInfo_ptr ret(new GroupInfo(USER_PRINCIPAL_GROUP, groupname));
        LDAPMessage *group_entry; //doesn't need free
        group_entry = ldap_first_entry(ld, search_result);

        ret->name = get_first_attr(group_entry,
                PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP));

        if (ret->name.length() == 0) {
            //how did the search find this? weird.
            string msg("Missing required group name attribute '"
                       + PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP)
                       + "' in value");
            lg.err("%s", msg.c_str());
            return boost::bind(eb, REMOTE_ERROR, msg);
        }

        ret->description = get_first_attr(group_entry,
                PROP_FIRST_STR(props, LD_UGDESC_FIELD_PROP));

        if (PROP_FIRST_STR(props, LD_UGMEMBER_FIELD_PROP).length()) {
            //get members
            berval **vals = ldap_get_values_len(ld, group_entry, 
                    PROP_FIRST_STR(props, LD_UGMEMBER_FIELD_PROP).c_str());
            int membercount = ldap_count_values_len(vals);
            for (int i = 0; i < membercount; ++i) {
                string member_str = string(vals[i]->bv_val, vals[i]->bv_len);
                if (PROP_FIRST_INT(props, LD_GROUP_POSIX_MODE_PROP)) {
                    ret->members.insert(member_str);
                }
                else {
                    string name = name_from_dn(member_str,
                            PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP),
                            PROP_FIRST_STR(props, LD_USER_FILTER_PROP),
                            PROP_FIRST_INT(props, LD_UNAME_IS_FIRST_RDN_PROP),
                            deadline_tv, ntries);
                    if (!name.empty()) {
                        ret->members.insert(name);
                    }
                }
            }
            ldap_value_free_len(vals);
        }
        if (PROP_FIRST_INT(props, LD_GROUP_POSIX_MODE_PROP)) {
            //get names for all user entries with corresponding
            //gidNumber attribute
            string gid = get_first_attr(group_entry, "gidNumber");
            if (!gid.empty()) {
                string queryfilter = "(gidNumber=" +
                        sanitize_string(gid, false) + ")";
                DnToAttrMap dn2attr = _do_search_users(queryfilter,
                        deadline_tv, ntries);
                BOOST_FOREACH(DnToAttrMap::value_type v, dn2attr) {
                    ret->members.insert(v.second);
                }
            }
        }

        if (PROP_FIRST_STR(props, LD_UGSUBGROUP_FIELD_PROP).length()) {
            //get subgroups
            berval **vals = ldap_get_values_len(ld, group_entry, 
                    PROP_FIRST_STR(props, LD_UGSUBGROUP_FIELD_PROP).c_str());
            int sgcount = ldap_count_values_len(vals);
            for (int i = 0; i < sgcount; ++i) {
                string dn_str = string(vals[i]->bv_val, vals[i]->bv_len);
                string name = name_from_dn(dn_str,
                        PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP),
                        PROP_FIRST_STR(props, LD_GROUP_FILTER_PROP),
                        PROP_FIRST_INT(props, LD_UGNAME_IS_FIRST_RDN_PROP),
                        deadline_tv, ntries);
                if (!name.empty()) {
                    ret->subgroups.insert(name);
                }
            }
            ldap_value_free_len(vals);
        }

        return boost::bind(cb, ret);
    }
    catch (LdapDirectoryException& e) {
        lg.err("Error in get_user_group: %s", e.what());
        if (is_recoverable_error(e.get_code())) {
            if (ntries > 1) {
                usleep(PROP_FIRST_INT(props, LD_OP_RETRY_DELAY_PROP));
                lg.err("Retrying query due to previous error");
                return get_user_group(groupname, deadline_tv, ntries-1,
                        cb, eb);
            }
            else {
                lg.err("Maximum retry count reached, returning with failure");
            }
        }
        return boost::bind(eb, e.get_directory_error(), string(e.what()));
    }
    catch (exception& e) {
        lg.err("Exception in get_user_group: %s", e.what());
        return boost::bind(eb, UNKNOWN_ERROR, string(e.what()));
    }
}

/*****************************************************************************/
/*****************************************************************************/


Ldap_proxy::Ldap_proxy(container::Component* c, const string& name,
        uint64_t config_id, storage::Async_transactional_storage *tstorage)
        : component(c), name(name), config_id(config_id), tstorage(tstorage), 
          props_valid(false), props_err_msg("Not yet initialized")
{
    set_default_props(default_props);
    props = new configuration::Properties(tstorage, get_prop_section(),
            default_props);

    //launch and add worker threads
    for (int i = 0; i < LDAP_THREADS; ++i) {
        ldapproxy[i] = new Ldap_proxy_s(props);
        ntp.add_worker(ldapproxy[i], 0);
    }
}

void
Ldap_proxy::set_default_props(
        configuration::Properties::Default_value_map& prop_map)
{
    prop_map[LD_URI_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_VERSION_PROP] = SINGLE_PROP_LIST(int64_t(3));
    prop_map[LD_OP_TO_PROP] = SINGLE_PROP_LIST(int64_t(10));
    prop_map[LD_OP_RETRY_PROP] = SINGLE_PROP_LIST(int64_t(2));
    prop_map[LD_OP_RETRY_DELAY_PROP] = SINGLE_PROP_LIST(int64_t(1000));

    prop_map[LD_BASE_DN_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_BROWSER_USER_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_BROWSER_USER_PW_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_USER_FILTER_PROP] =
            SINGLE_PROP_LIST(string("objectClass=organizationalPerson"));
    prop_map[LD_UNAME_FIELD_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_USER_LOOKUP_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_UNAME_IS_FIRST_RDN_PROP] = SINGLE_PROP_LIST(int64_t(0));
    prop_map[LD_UID_FIELD_PROP] = SINGLE_PROP_LIST(string("uidNumber"));
    prop_map[LD_NAME_FIELD_PROP] = SINGLE_PROP_LIST(string("cn"));
    prop_map[LD_PHONE_FIELD_PROP] = SINGLE_PROP_LIST(string("telephoneNumber"));
    prop_map[LD_EMAIL_FIELD_PROP] = SINGLE_PROP_LIST(string("mail"));
    prop_map[LD_LOC_FIELD_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_DESC_FIELD_PROP] = SINGLE_PROP_LIST(string("gecos"));

    prop_map[LD_USER_OBJ_GROUPS_ATTR_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_GROUP_FILTER_PROP] =
            SINGLE_PROP_LIST(string("objectClass=group"));
    prop_map[LD_UGNAME_FIELD_PROP] = SINGLE_PROP_LIST(string("cn"));
    prop_map[LD_UGNAME_IS_FIRST_RDN_PROP] = SINGLE_PROP_LIST(int64_t(0));
    prop_map[LD_UGDESC_FIELD_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_UGMEMBER_FIELD_PROP] = SINGLE_PROP_LIST(string("member"));
    prop_map[LD_UGSUBGROUP_FIELD_PROP] = SINGLE_PROP_LIST(string("member"));
    prop_map[LD_GROUP_BASE_DN_PROP] = SINGLE_PROP_LIST(string(""));
    prop_map[LD_GROUP_POSIX_MODE_PROP] = SINGLE_PROP_LIST(int64_t(0));
    prop_map[LD_SEARCH_SUBTREE_PROP] = SINGLE_PROP_LIST(int64_t(1));
    prop_map[LD_USE_SSL_PROP] = SINGLE_PROP_LIST(int64_t(1));
    prop_map[LD_FOLLOW_REFERRALS_PROP] = SINGLE_PROP_LIST(int64_t(0));

    prop_map[LD_ENABLED_AUTH_SIMPLE] = SINGLE_PROP_LIST(int64_t(1));
    prop_map[LD_ENABLED_USER] = SINGLE_PROP_LIST(Directory::READ_ONLY_SUPPORT);
    prop_map[LD_ENABLED_USER_GROUP] = 
            SINGLE_PROP_LIST(Directory::READ_ONLY_SUPPORT);
}


Directory::Directory_Status
Ldap_proxy::get_status() {
    if (!PROP_FIRST_STR(props, LD_URI_PROP).length()) {
        props_err_msg = "Dirctory '"+name+"' missing required URI property";
        lg.warn("%s", props_err_msg.c_str());
        return Directory::INVALID;
    }
    if (!is_ldaps(PROP_FIRST_STR(props, LD_URI_PROP))
        && PROP_FIRST_INT(props, LD_USE_SSL_PROP)
        && PROP_FIRST_INT(props, LD_VERSION_PROP) != 3)
    {
        props_err_msg = "Dirctory '"+name+"' cannot use SSL in LDAPv2; use "
                        "v3 or ldaps://";
        lg.warn("%s", props_err_msg.c_str());
        return Directory::INVALID;
    }
    if (!PROP_FIRST_STR(props, LD_BASE_DN_PROP).length()) {
        props_err_msg = "Dirctory '"+name+"' missing required User Base DN "
                        "property";
        lg.warn("%s", props_err_msg.c_str());
        return Directory::INVALID;
    }
    if (!PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP).length()) {
        props_err_msg = "Dirctory '"+name+"' missing required username field "
                        "property";
        lg.warn("%s", props_err_msg.c_str());
        return Directory::INVALID;
    }
    if (PROP_FIRST_INT(props, LD_VERSION_PROP) != 2 && 
            PROP_FIRST_INT(props, LD_VERSION_PROP) != 3) {
        props_err_msg = "Dirctory '"+name+"' has invalid LDAP version property";
        lg.warn("%s", props_err_msg.c_str());
        return Directory::INVALID;
    }
    
    //check URI
    LDAP *testld;
    int rc = ldap_initialize(&testld,
            PROP_FIRST_STR(props, LD_URI_PROP).c_str());
    if (rc != LDAP_SUCCESS) {
        props_err_msg = "Failed to parse URI '" +
                PROP_FIRST_STR(props, LD_URI_PROP) + "' for directory '" +
                name + "'";
        lg.warn("%s", props_err_msg.c_str());

        return Directory::INVALID;
    }
    if (testld != NULL) {
        ldap_unbind_ext_s(testld, NULL, NULL);
    }

    //TODO: Try a search to validate bind
    props_err_msg = "";
    return Directory::OK;
}

vector<string>
Ldap_proxy::get_enabled_auth_types() {
    vector<string> ret;
    if (PROP_FIRST_INT(props, LD_ENABLED_AUTH_SIMPLE)) {
        ret.push_back(AUTH_SIMPLE);
    }
    return ret;
}

static void
props_commit_cb(Properties_ptr props, Result_callback& cb) {
    cb();
}

static void
set_enabled_auth_types_cb(const AuthSupportSet& supp, Properties_ptr props,
        const Enabled_auth_types_cb& cb, const Errback& eb)
{
    std::set<std::string>::iterator supp_iter;
    AuthSupportSet newsupp;
    int64_t auth_simple = 0;
    for (supp_iter = supp.begin(); supp_iter != supp.end(); supp_iter++) {
        if (*supp_iter == AUTH_SIMPLE) {
            auth_simple = 1;
            newsupp.insert(LD_ENABLED_AUTH_SIMPLE);
        }
        else {
            lg.warn("Ignoring unsupported authentication type '%s' in "
                    "set_enabled_auth_types.", supp_iter->c_str());
        }
    }
    configuration::Property_list_ptr plp = 
            props->get_value(LD_ENABLED_AUTH_SIMPLE);
    plp->clear();
    plp->push_back(configuration::Property(auth_simple));

    const Result_callback rcb = boost::bind(cb, newsupp);
    props->async_commit(
            boost::bind(props_commit_cb, props, rcb),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to write configuration"));
}

bool
Ldap_proxy::set_enabled_auth_types(const AuthSupportSet& supp,
        const Enabled_auth_types_cb& cb, const Errback& eb)
{
    lg.dbg("Setting enabled auth types");
    Properties_ptr rwprops(new configuration::Properties(
            tstorage, get_prop_section(), default_props));
    rwprops->async_begin(
            boost::bind(set_enabled_auth_types_cb, supp, rwprops, cb, eb),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to read configuration"));
    return true;
}

static void
nop_cb(configuration::Properties*) {
    //NOP
}

static void
nop_eb(DirectoryError err, const std::string& msg) {
    lg.warn("Unhandled error %d: %s", err, msg.c_str());
}

void
Ldap_proxy::update_config_status_cb(const Directory::ConfigCb& cb,
         const Errback& eb) {
    props->async_add_callback(boost::bind(&Ldap_proxy::props_updated_cb, this,
                nop_cb, nop_eb),
            boost::bind(cb, props),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to add property change "
                    "listener"));
    reinit();
}

void
Ldap_proxy::update_config_status(const Directory::ConfigCb& cb,
        const Errback& eb) {
    lg.dbg("Properties updated, checking config status");
    props_valid = get_status() == Directory::OK;
    std::string user_group_enabled;
    if (!props_valid or !user_groups_configured()) {
        user_group_enabled = NO_SUPPORT;
    }
    else {
        user_group_enabled = PROP_FIRST_STR(props, LD_ENABLED_USER);
    }
    lg.dbg("Setting user group status in '%s' to %s", name.c_str(),
            user_group_enabled.c_str());
    configuration::Property_list_ptr plp =
            props->get_value(LD_ENABLED_USER_GROUP);
    plp->clear();
    plp->push_back(configuration::Property(user_group_enabled));
    props->async_commit(
            boost::bind(&Ldap_proxy::update_config_status_cb, this, cb, eb),
            boost::bind(eb, UNKNOWN_ERROR,
                "Failed to write principal status"));
}

void
Ldap_proxy::props_updated_cb(const Directory::ConfigCb& cb,
        const Errback& eb) {
    props->async_begin(
            boost::bind(&Ldap_proxy::update_config_status, this, cb, eb),
            boost::bind(eb, UNKNOWN_ERROR,
                "Failed to update principal status"));
}

void
Ldap_proxy::prop_begin_cb(const Directory::ConfigCb& cb,
        const Errback& eb)
{
    //we commit the props so defaults are in the db for UI config page
    props->async_commit(
            boost::bind(&Ldap_proxy::props_updated_cb, this, cb, eb),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to write configuration"));
}

bool 
Ldap_proxy::configure(const ConfigCb& cb, const Errback& eb) {
    props->async_begin(boost::bind(&Ldap_proxy::prop_begin_cb, this, cb, eb),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to update configuration"));
    return true;
}

static void async_cb(const Result_callback& cb) {
    cb();
} 

void
Ldap_proxy::simple_auth(const string& username, const string& password,
                         const Simple_auth_callback& cb)
{
    //TODO: add a errback to this method for proper error reporting
    try {
        if (!props_valid) {
            throw runtime_error("Invalid configuration");
        }
        ntp.execute(boost::bind(&Ldap_proxy_s::simple_auth, _1, username,
                    password, cb, int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    get_to_tv()), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("Exception during simple_auth: %s\n", e.what());
        AuthResult authres(AuthResult::SERVER_ERROR, username);
        cb(authres);
    }
}

/****************************************************************************/

const PrincipalSupportMap
Ldap_proxy::get_enabled_principals() {
    PrincipalSupportMap ret;
    ret[SWITCH_PRINCIPAL] = NO_SUPPORT;
    ret[LOCATION_PRINCIPAL] = NO_SUPPORT;
    ret[HOST_PRINCIPAL] = NO_SUPPORT;
    ret[USER_PRINCIPAL] = PROP_FIRST_STR(props, LD_ENABLED_USER);
    return ret;
}

std::string
Ldap_proxy::principal_enabled(int principal_type) {
    if (principal_type == int(USER_PRINCIPAL)) {
        return PROP_FIRST_STR(props, LD_ENABLED_USER);
    }
    return Directory::NO_SUPPORT;
}

static void
set_enabled_principals_cb(const PrincipalSupportMap& supp, Properties_ptr props,
        const Principal_support_cb& cb, const Errback& eb)
{
    PrincipalSupportMap newsupp;
    PrincipalSupportMap::const_iterator sm_iter;
    for (sm_iter = supp.begin(); sm_iter != supp.end(); sm_iter++) {
        if (sm_iter->first == USER_PRINCIPAL) {
            newsupp[sm_iter->first] = sm_iter->second;
            configuration::Property_list_ptr plp =
                    props->get_value(LD_ENABLED_USER);
            plp->clear();
            plp->push_back(configuration::Property(sm_iter->second));
            plp = props->get_value("enabled_user_principal_group");
            plp->clear();
            plp->push_back(configuration::Property(sm_iter->second));
        }
        else if (sm_iter->second != NO_SUPPORT) {
            lg.warn("Ignoring unsupported principal type '%d' in "
                    "set_enabled_principals.", sm_iter->first);
        }
    }
    const Result_callback rcb = boost::bind(cb, newsupp);
    props->async_commit(
            boost::bind(props_commit_cb, props, rcb),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to write configuration"));
}

bool
Ldap_proxy::set_enabled_principals(const PrincipalSupportMap& supp, 
        const Principal_support_cb& cb, const Errback& eb) {
    lg.dbg("Updating enabled principal types");
    Properties_ptr rwprops(new configuration::Properties(
            tstorage, get_prop_section(), default_props));
    rwprops->async_begin(
            boost::bind(set_enabled_principals_cb, supp, rwprops, cb, eb),
            boost::bind(eb, UNKNOWN_ERROR, "Failed to update configuration"));
    return true;
}

bool
Ldap_proxy::get_principal(Principal_Type ptype, std::string principal_name,
        const Get_principal_cb& cb, const Errback& eb)
{
    try {
        if (!props_valid) {
            eb(INVALID_CONFIGURATION, props_err_msg.c_str());
            return true;
        }
        if (ptype != USER_PRINCIPAL) {
            ostringstream msg;
            msg << "Principal type " << ptype << " not supported";
            lg.warn("%s", msg.str().c_str());
            eb(OPERATION_NOT_PERMITTED, msg.str());
            return true;
        }
        ntp.execute(boost::bind(&Ldap_proxy_s::get_user, _1, principal_name,
                    get_to_tv(), int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    cb, eb), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("search_principals failed: %s", e.what());
        eb(UNKNOWN_ERROR, string(e.what()));
    }
    return true;
}

string
Ldap_proxy::user_query_to_filter(PrincipalQuery query) {
    /* By convention, we ignore filter parameters that do not have a
     * corresponding LDAP attribute set.
     */
    ostringstream filter;

    BOOST_FOREACH(PrincipalQuery::value_type v, query) {
        string val = sanitize_string(v.second, false);
        if (v.first == "name") {
            filter << "(" << PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP)
                   << "=" << val << ")";
        }
        else if (v.first == "name_glob") {
            string globval = sanitize_string(v.second, true);
            filter << "(" << PROP_FIRST_STR(props, LD_UNAME_FIELD_PROP)
                   << "=" << globval << ")";
        }
        else if (v.first == "user_id") {
            if (PROP_FIRST_STR(props, LD_UID_FIELD_PROP).length()) {
                filter << "(" << PROP_FIRST_STR(props, LD_UID_FIELD_PROP)
                       << "=" << val << ")";
            }
        }
        else if (v.first == "user_real_name") {
            if (PROP_FIRST_STR(props, LD_NAME_FIELD_PROP).length()) {
                filter << "(" << PROP_FIRST_STR(props, LD_NAME_FIELD_PROP)
                       << "=" << val << ")";
            }
        }
        else if (v.first == "phone") {
            if (PROP_FIRST_STR(props, LD_PHONE_FIELD_PROP).length()) {
                filter << "(" << PROP_FIRST_STR(props, LD_PHONE_FIELD_PROP)
                       << "=" << val << ")";
            }
        }
        else if (v.first == "user_email") {
            if (PROP_FIRST_STR(props, LD_EMAIL_FIELD_PROP).length()) {
                filter << "(" << PROP_FIRST_STR(props, LD_EMAIL_FIELD_PROP)
                       << "=" << val << ")";
            }
        }
        else if (v.first == "location") {
            if (PROP_FIRST_STR(props, LD_LOC_FIELD_PROP).length()) {
                filter << "(" << PROP_FIRST_STR(props, LD_LOC_FIELD_PROP)
                       << "=" << val << ")";
            }
        }
        else if (v.first == "description") {
            if (PROP_FIRST_STR(props, LD_DESC_FIELD_PROP).length()) {
                filter << "(" << PROP_FIRST_STR(props, LD_DESC_FIELD_PROP)
                       << "=" << val << ")";
            }
        }
        else {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported query key '" + v.first + "'");
        }
    }
    return filter.str();
}

bool
Ldap_proxy::search_principals(Principal_Type ptype, PrincipalQuery query,
        const Principal_set_cb& cb, const Errback& eb)
{
    try {
        if (!props_valid) {
            eb(INVALID_CONFIGURATION, props_err_msg.c_str());
            return true;
        }
        if (ptype != USER_PRINCIPAL) {
            eb(OPERATION_NOT_PERMITTED, "Unsupported principal type "
                    + int(ptype));
            return true;
        }
        string filter = user_query_to_filter(query);
        ntp.execute(boost::bind(&Ldap_proxy_s::search_users, _1, filter,
                    get_to_tv(), int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    cb, eb), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("search_principals failed: %s", e.what());
        eb(UNKNOWN_ERROR, string(e.what()));
    }
    return true;
}

/****************************************************************************/

const GroupSupportMap
Ldap_proxy::get_enabled_groups() {
    GroupSupportMap ret;
    ret[SWITCH_PRINCIPAL_GROUP] = NO_SUPPORT;
    ret[LOCATION_PRINCIPAL_GROUP] = NO_SUPPORT;
    ret[HOST_PRINCIPAL_GROUP] = NO_SUPPORT;
    ret[DLADDR_GROUP] = NO_SUPPORT;
    ret[NWADDR_GROUP] = NO_SUPPORT;
    ret[USER_PRINCIPAL_GROUP] = 
            PROP_FIRST_STR(props, LD_ENABLED_USER_GROUP);
    return ret;
}

std::string
Ldap_proxy::group_enabled(int group_type) {
    try {
        if (group_type == int(USER_PRINCIPAL_GROUP) &&
                user_groups_configured())
        {
            return PROP_FIRST_STR(props, LD_ENABLED_USER_GROUP);
        }
    }
    catch (exception& e) {
        lg.warn("group_enabled failed: %s", e.what());
    }
    return Directory::NO_SUPPORT;
}

bool
Ldap_proxy::get_group_membership(Group_Type gtype, std::string member,
        const Group_set_cb& cb, const Errback& eb)
{
    try {
        if (!props_valid) {
            eb(INVALID_CONFIGURATION, props_err_msg.c_str());
            return true;
        }
        if (!user_groups_configured()) {
            cb(Group_name_set());
            return true;
        }
        if (gtype != USER_PRINCIPAL_GROUP) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported group type " + int(gtype));
        }
        ntp.execute(boost::bind(&Ldap_proxy_s::get_group_membership, _1,
                    member, get_to_tv(),
                    int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    cb, eb), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("get_group_membership failed: %s", e.what());
        eb(UNKNOWN_ERROR, string(e.what()));
    }
    return true;
}

string
Ldap_proxy::group_query_to_filter(GroupQuery query) {
    /* By convention, we ignore filter parameters that do not have a
     * corresponding LDAP attribute set.
     */
    ostringstream filter;

    BOOST_FOREACH(PrincipalQuery::value_type v, query) {
        string val = sanitize_string(v.second, false);
        if (v.first == "name") {
            filter << "(" << PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP)
                   << "=" << val << ")";
        }
        else if (v.first == "name_glob") {
            string globval = sanitize_string(v.second, true);
            filter << "(" << PROP_FIRST_STR(props, LD_UGNAME_FIELD_PROP)
                   << "=" << globval << ")";
        }
        else {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported query key '" + v.first + "'");
        }
    }
    return filter.str();
}

bool
Ldap_proxy::search_groups(Group_Type gtype, GroupQuery query,
        const Group_set_cb& cb, const Errback& eb)
{
    try {
        if (!props_valid) {
            eb(INVALID_CONFIGURATION, props_err_msg.c_str());
            return true;
        }
        if (gtype != USER_PRINCIPAL_GROUP) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported group type " + int(gtype));
        }
        if (!user_groups_configured()) {
            cb(Group_name_set());
            return true;
        }
        string filter = group_query_to_filter(query);
        ntp.execute(boost::bind(&Ldap_proxy_s::search_user_groups, _1, filter,
                    get_to_tv(), int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    cb, eb), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("search_groups failed: %s", e.what());
        eb(UNKNOWN_ERROR, string(e.what()));
    }
    return true;
}

bool
Ldap_proxy::get_group(Group_Type gtype, std::string groupname,
        const Get_group_cb& cb, const Errback& eb)
{
    try {
        if (!props_valid) {
            eb(INVALID_CONFIGURATION, props_err_msg.c_str());
            return true;
        }
        if (gtype != USER_PRINCIPAL_GROUP) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported group type " + int(gtype));
        }
        if (!user_groups_configured()) {
            cb(GroupInfo_ptr());
            return true;
        }
        ntp.execute(boost::bind(&Ldap_proxy_s::get_user_group, _1, groupname,
                    get_to_tv(), int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    cb, eb), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("get_group failed: %s", e.what());
        eb(UNKNOWN_ERROR, string(e.what()));
    }
    return true;
}

bool
Ldap_proxy::get_group_parents(Group_Type gtype, std::string groupname,
        const Group_set_cb& cb, const Errback& eb)
{
    try {
        if (!props_valid) {
            eb(INVALID_CONFIGURATION, props_err_msg.c_str());
            return true;
        }
        if (gtype != USER_PRINCIPAL_GROUP) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported group type " + int(gtype));
        }
        if (!user_groups_configured()) {
            cb(Group_name_set());
            return true;
        }
        ntp.execute(boost::bind(&Ldap_proxy_s::get_group_parents, _1, groupname,
                    get_to_tv(), int(PROP_FIRST_INT(props, LD_OP_RETRY_PROP)),
                    cb, eb), boost::bind(&async_cb, _1));
    }
    catch (exception& e) {
        lg.warn("get_group_parents failed: %s", e.what());
        eb(UNKNOWN_ERROR, string(e.what()));
    }
    return true;
}





