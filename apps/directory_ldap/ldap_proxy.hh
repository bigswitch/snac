/*
 * Copyright 2008 (C) Nicira, Inc.
 */
#ifndef LDAP_PROXY_HH
#define LDAP_PROXY_HH

#ifdef TWISTED_ENABLED
#include <Python.h>
#else
class PyObject;
#endif

#include <list>
#include <map>
#include <set>
#include <string>
#include <sstream>

#include <ldap.h>

#include <boost/function.hpp>
#include <boost/shared_ptr.hpp>

#include "configuration/properties.hh"
#include "hash_map.hh"
#include "storage/transactional-storage.hh"
#include "threads/cooperative.hh"
#include "threads/native-pool.hh"
#include "timeval.hh"
#include "directory/directory.hh"
#include "directory/principal_types.hh"

#define PROP_FIRST_INT(props, key) \
        boost::get<int64_t>((*((props)->get_value(key)))[0].get_value())
#define PROP_FIRST_STR(props, key) \
        boost::get<std::string>((*((props)->get_value(key)))[0].get_value())
#define PROP_FIRST_FLOAT(props, key) \
        boost::get<double>((*((props)->get_value(key)))[0].get_value())
#define SINGLE_PROP_LIST(val) \
        vector<configuration::Property>(1, configuration::Property(val))

namespace vigil {
namespace applications {
namespace directory {

/*********************************
 * General Configuration Options *
 *********************************/
/* Properties section will be <PROPERTIES_SECTION_PREFIX><config_id> */
extern const std::string LD_PROP_SECTION_PREFIX;

/* URI to remote LDAP server */
extern const std::string LD_URI_PROP;

/* either 2 or 3 */
extern const std::string LD_VERSION_PROP;

/* total sec for operation including retries */
extern const std::string LD_OP_TO_PROP;

/* # each op should be reissue if error */
extern const std::string LD_OP_RETRY_PROP;

/* delay between retries */
extern const std::string LD_OP_RETRY_DELAY_PROP;

/**********************
 * User Entry Options *
 **********************/
/* base dn for user searches */
extern const std::string LD_BASE_DN_PROP;

/**
 * browser_user{bind_d,bind_password} is the account to use for binding
 * for the purpose of performing user account searches.  If not
 * specified, an anonymous bind will be attempted.
 */
extern const std::string LD_BROWSER_USER_PROP;
extern const std::string LD_BROWSER_USER_PW_PROP;

/* username attribute on user entry */
extern const std::string LD_UNAME_FIELD_PROP;

/* optional query used to find user entity */
extern const std::string LD_USER_LOOKUP_PROP;

/* optimize DN->name resolution if name can always be extracted from the DN */
extern const std::string LD_UNAME_IS_FIRST_RDN_PROP;

/* user id (UID) attribute on user entry */
extern const std::string LD_UID_FIELD_PROP;
/* user real name attribute on user entry */
extern const std::string LD_NAME_FIELD_PROP;
/* user phone attribute on user entry */
extern const std::string LD_PHONE_FIELD_PROP;
/* user email attribute on user entry */
extern const std::string LD_EMAIL_FIELD_PROP;
/* user location attribute on user entry */
extern const std::string LD_LOC_FIELD_PROP;
/* user description attribute on user entry */
extern const std::string LD_DESC_FIELD_PROP;

/**
 * Optional additional filter to use during user entry searches.
 * The search filter will be constructed as:
 *  (&(username_field=<USERNAME>)&search_filter)
 */
extern const std::string LD_USER_FILTER_PROP;

/******************
 * Groups Options *
 ******************/
/**
 * if set, query groups directly from the user object
 *
 * common values:
 *  Active Directory     : memberOf
 *  IBM Directory Server : ibm-allgroups
 */
extern const std::string LD_USER_OBJ_GROUPS_ATTR_PROP; 

/**
 * Search filter used to find groups if user_object_groups_attribute
 * is not specified (empty string)
 *
 * common values:
 *  Domino LDAP      : objectclass=groupofnames
 *  IBM LDAP         : objectclass=groupofuniquenames
 *  Active Directory : objectclass=group
 */
extern const std::string LD_GROUP_FILTER_PROP;

/**
 * Base DN to use for group searches
 *
 * common values:
 *  Domino LDAP : <can be empty string>
 *  IBM LDAP    : dc=company,dc=com
 */
extern const std::string LD_GROUP_BASE_DN_PROP;

/* group name attribute on group entry */
extern const std::string LD_UGNAME_FIELD_PROP;
/* optimize DN->name resolution if name can always be extracted from the DN */
extern const std::string LD_UGNAME_IS_FIRST_RDN_PROP;

/* group description attribute on group entry */
extern const std::string LD_UGDESC_FIELD_PROP;
/* group member attribute on group entry */
extern const std::string LD_UGMEMBER_FIELD_PROP;
/* group subgroup attribute on group entry */
extern const std::string LD_UGSUBGROUP_FIELD_PROP;

/*
 * if True, groups membership is associated by username, else, group
 * membership is associated by user entry DN
 */
extern const std::string LD_GROUP_POSIX_MODE_PROP;

/* search SUBTREE, else search ONELEVEl */
extern const std::string LD_SEARCH_SUBTREE_PROP;

/* connect via SSL, else connect plaintext */
extern const std::string LD_USE_SSL_PROP;

/* follow referrals, else don't */
extern const std::string LD_FOLLOW_REFERRALS_PROP;

/**************************
 * Support enabled status *
 **************************/
extern const std::string LD_ENABLED_AUTH_SIMPLE;
extern const std::string LD_ENABLED_USER;
extern const std::string LD_ENABLED_USER_GROUP;
extern const std::string LD_OP_TO_PROP;

/****************************************************************************/

static const int LDAP_THREADS = 3;

/****************************************************************************/

typedef std::map<std::string, std::string> DnToAttrMap;

typedef boost::function<void()> Result_callback;
typedef hash_map<std::string, std::string> GroupToRoleMap;

//TODO: types should be defined in directory.hh
typedef boost::shared_ptr<PrincipalInfo> PrincipalInfo_ptr;
typedef boost::shared_ptr<SwitchInfo> SwitchInfo_ptr;
typedef boost::shared_ptr<LocationInfo> LocationInfo_ptr;
typedef boost::shared_ptr<NetInfo> NetInfo_ptr;
typedef boost::shared_ptr<HostInfo> HostInfo_ptr;
typedef boost::shared_ptr<UserInfo> UserInfo_ptr;
typedef boost::shared_ptr<GroupInfo> GroupInfo_ptr;
typedef boost::function<void(const PrincipalInfo_ptr)> Get_principal_cb;
typedef boost::function<void(const Principal_name_set&)> Principal_set_cb;
typedef boost::function<void(const AuthSupportSet&)> Enabled_auth_types_cb;
typedef boost::function<void(const PrincipalSupportMap&)> Principal_support_cb;
typedef boost::function<void(const GroupSupportMap&)> Group_support_cb;
typedef boost::function<void(const Group_name_set&)> Group_set_cb;
typedef boost::function<void(const GroupInfo_ptr)> Get_group_cb;
typedef boost::function<void(DirectoryError, std::string)> Errback;

typedef boost::shared_ptr<configuration::Properties> Properties_ptr;

class LdapDirectoryException : public std::exception {
public:
    LdapDirectoryException(int cd, std::string m)
            : code(cd), msg(m) {}
    ~LdapDirectoryException() throw() {}
    const char* what() const throw() { return msg.c_str(); }
    int get_code() { return code; }

    DirectoryError get_directory_error() {
        switch (code) {
            case LDAP_BUSY:
            case LDAP_NOT_SUPPORTED:
            case LDAP_UNWILLING_TO_PERFORM:
                return REMOTE_ERROR;
            case LDAP_CONNECT_ERROR:
            case LDAP_TIMEOUT:
            case LDAP_UNAVAILABLE:
            case LDAP_SERVER_DOWN:
            case LDAP_LOOP_DETECT:
                return COMMUNICATION_ERROR;
            default:
                return UNKNOWN_ERROR;
        }
    }

private:
    int code;
    std::string msg;
};

/**
 * Synchronous LDAP directory proxy module
 *
 * Uses OpenLDAP client API to exposing various directory operations
 * such as authentication and group membership lookup
 *
 */
class Ldap_proxy_s {
public:
    Ldap_proxy_s(configuration::Properties *props);
    ~Ldap_proxy_s();

    void reinit() { needs_init = true; }

    /**
     * Perform a basic username/password verification and group lookup
     *
     * Validates username/password using underlying directory by looking
     * up DN for username and performing a simple bind
     *
     */
    Result_callback simple_auth(const std::string &username,
            const std::string &password,
            const Simple_auth_callback& callback,
            int ntries, const timeval& deadline_tv);

    Result_callback search_users(const std::string &filter,
            const timeval& deadline_tv, int ntries,
            const Principal_set_cb&, const Errback&);

    Result_callback get_user(const std::string &username,
            const timeval& deadline_tv, int ntries,
            const Get_principal_cb&, const Errback&);

    Result_callback get_group_membership(const std::string &username, 
            const timeval& deadline_tv, int ntries,
            const Group_set_cb&, const Errback&);

    Result_callback search_user_groups(const std::string &filter,
            const timeval& deadline_tv, int ntries,
            const Group_set_cb&, const Errback&);

    Result_callback get_user_group(const std::string &groupname,
            const timeval& deadline_tv, int ntries,
            const Get_group_cb& cb, const Errback& eb);

    Result_callback get_group_parents(const std::string &groupname,
            const timeval& deadline_tv, int ntries,
            const Group_set_cb& cb, const Errback& eb);
private:
    int init();
    int bind_as_browser_user(const timeval& deadline_tv, int ntries);
    int simple_bind_with_deadline(const std::string& userdn,
            const std::string& password, const timeval& deadline_tv,
            int ntries, bool allowAnonymous);
    int get_entities_by_name(const std::string& basequery,
            const std::string& basedn, const std::string& filter,
            LDAPMessage **message,
            const timeval& deadline_tv, int ntries);
    const Group_name_set get_groups_for_user_entry(LDAPMessage *user_entry,
           const timeval& deadline_tv, int ntries);
    std::string get_first_attr(LDAPMessage *entry, std::string key);
    std::string name_from_dn(const std::string& dn_str,
            const std::string& nameattr,  const std::string& filter,
            bool use_first_rdn, const timeval& deadline_tv, int ntries);
    int get_user_entity(const std::string& username,
            LDAPMessage **message, const timeval& deadline_tv, int ntries);
    int get_user_group_entity(const std::string& usergroupname,
            LDAPMessage **message, const timeval& deadline_tv, int ntries);

    std::map<std::string, std::string> get_attr_vals(const std::string& basedn, 
        const std::string& entityfilter, const std::string& attr_name,
        int scope, const timeval& deadline_tv, int ntries);

    DnToAttrMap _do_search_users(const std::string &filter,
            const timeval& deadline_tv, int ntries);

    DnToAttrMap _do_search_user_groups(const std::string &filter,
            const timeval& deadline_tv, int ntries);

    configuration::Properties *props;
    LDAP *ld;
    bool needs_init;
    std::string currently_bound_user;
};

/****************************************************************************/

/*
 * Asynchronous LDAP directory proxy module
 *
 * Exposes various directory operations such as authentication and group
 * membership lookup.
 *
 * Wraps blocking client operations (via Ldap_proxy_s) for execution in a
 * separate thread.
 *
 */
class Ldap_proxy {
//TODO extend : public Directory once the constants are cleaned out of there
public:
    //TODO: the following block can go away when we exted Directory
    typedef std::map<std::string, std::string> ConfigParamMap;
    typedef boost::function<void(configuration::Properties*)> ConfigCb;
    enum Directory_Status {
        UNKNOWN = 0,
        OK,
        INVALID
    };

    // Initialize prop_map with default properties
    static void set_default_props(
            configuration::Properties::Default_value_map& prop_map);

    Ldap_proxy(container::Component* component, const std::string& name,
            uint64_t config_id, storage::Async_transactional_storage *tstorage);

    bool configure(const ConfigCb&, const Errback&);

    void reinit() {
      for (int i = 0; i < LDAP_THREADS; ++i) {
        ldapproxy[i]->reinit();
      }
    }

    // this must be called before deleting the object
    void shutdown(const boost::function<void()> cb) {
      ntp.shutdown(cb);
    }

    ~Ldap_proxy() {
      for (int i = 0; i < LDAP_THREADS; ++i) {
        delete ldapproxy[i];
      }
    }

    /********************
     * Meta information *
     ********************/
    configuration::Properties* get_properties() {
        return props;
    }

    const std::string get_prop_section() {
        std::stringstream ss;
        ss << LD_PROP_SECTION_PREFIX << config_id;
        return ss.str();
    }

    const configuration::Properties::Default_value_map get_default_props() {
        return default_props;
    }

    //bool set_properties(const configuration::Properties*);

    Directory::Directory_Status get_status();

    /******************
     * Authentication *
     ******************/

    std::vector<std::string> get_enabled_auth_types();

    bool set_enabled_auth_types(const AuthSupportSet&,
            const Enabled_auth_types_cb& cb, const Errback& eb);

    /**
     * Perform a basic username/password verification and group lookup
     *
     * Validates username/password using underlying directory by looking
     * up DN for username and performing a simple bind
     *
     */
    void simple_auth(const std::string &username,
                     const std::string &password,
                     const Simple_auth_callback& cb);

    /**************
     * Principals *
     **************/

    const PrincipalSupportMap get_enabled_principals();

    std::string principal_enabled(int principal_type);

    bool set_enabled_principals(const PrincipalSupportMap&,
            const Principal_support_cb& cb, const Errback& eb);

    bool get_principal(Principal_Type, std::string principal_name,
            const Get_principal_cb& cb, const Errback& eb);

    bool search_principals(Principal_Type, PrincipalQuery,
            const Principal_set_cb&, const Errback&);

    /**********
     * Groups *
     **********/

    const GroupSupportMap get_enabled_groups();

    std::string group_enabled(int group_type);

    bool get_group_membership(Group_Type, std::string member,
            const Group_set_cb& cb, const Errback& eb);

    bool search_groups(Group_Type, GroupQuery, 
            const Group_set_cb& cb, const Errback& eb);

    bool get_group(Group_Type, std::string groupname,
            const Get_group_cb& cb, const Errback& eb);

    bool get_group_parents(Group_Type, std::string groupname, 
            const Group_set_cb& cb, const Errback& eb);

private:
    void props_updated_cb(const Directory::ConfigCb&, const Errback&);
    void update_config_status(const Directory::ConfigCb&, const Errback&);
    void update_config_status_cb(const Directory::ConfigCb&, const Errback&);

    void prop_begin_cb(const Directory::ConfigCb&, const Errback&);
    std::string user_query_to_filter(PrincipalQuery);
    std::string group_query_to_filter(GroupQuery);

    inline timeval get_to_tv() {
        timeval deadline_tv;
        ::gettimeofday(&deadline_tv, 0);
        deadline_tv.tv_sec += PROP_FIRST_INT(props, LD_OP_TO_PROP);
        return deadline_tv;
    }

    //may throw exception on properties error 
    inline bool user_groups_configured() {
        if (PROP_FIRST_STR(props, LD_GROUP_BASE_DN_PROP).length()) {
            return true;
        }
        return false;
    }

    container::Component* component;
    const std::string name;
    uint64_t config_id;
    Ldap_proxy_s* ldapproxy[LDAP_THREADS];
    Native_thread_pool<Result_callback, Ldap_proxy_s> ntp;

    storage::Async_transactional_storage *tstorage;
    configuration::Properties::Default_value_map default_props;
    configuration::Properties *props;
    bool props_valid;
    std::string props_err_msg;
};


} // namespace directory
} // namespace applications
} // namespace vigil

#endif /* LDAP_PROXY_HH */
