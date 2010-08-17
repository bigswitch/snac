#include "http_redirector.hh"

#include "assert.hh"
#include "datapath-join.hh"
#include "netinet++/datapathid.hh"
#include "netinet++/ethernet.hh"
#include "netinet++/ip.hh"
#include "netinet++/tcp.hh"
#include "netinet++/vlan.hh"
#include "storage/storage.hh"
#include "vlog.hh"

#include <algorithm>
#include <boost/bind.hpp>
#include <boost/format.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/shared_array.hpp>
#include <ctime>
#include <inttypes.h>
#include <iomanip>
#include <iostream>
#include <openssl/md5.h>

using namespace std;
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::configuration;
using namespace vigil::applications::storage;
using namespace vigil::container;

namespace vigil {
namespace applications {

/*
 * For now, the UI config page is easier to implement if the properties
 * section is the same as the captive portal.
 */
static const string PROPERTIES_SECTION("captive_portal_settings");
static const string REDIR_URL_PROP("redir_url");
static const string REDIR_URL_DEFAULT("https://authportal/cp/");
static const string RST_UNAUTH_PKT_PROP("rst_unauth_packets");
static const int64_t RST_UNAUTH_PKT_DEFAULT = 0;

static const string POLICY_FN_ID("http_redirect");
static const int HTTP_PORT = 80;
static const int INITIAL_IPID = 0;
static const int TCP_WIN = 1460;
static const int MIN_SUPPORTED_MSS = 512; /* SLIP Line / encap ppp */
static const int MAX_QUERY_LEN = 1024*20; /* Our tracking cookie wraps @ 64k */

static const char *redir_header_fmt =  
    "HTTP/1.1 302 Found\r\n"
    "Location: %s\r\n"
    "Cache-Control: no-cache\r\n"
    "Content-Type: text/html; charset=UTF-8\r\n"
    "Server: NOX\r\n"
    "Content-Length: %d\r\n"
    "Date: %s\r\n\r\n";

static const char *redir_payload_fmt = 
    "<HTML><HEAD><meta http-equiv=\"content-type\" "
    "content=\"text/html;charset=utf-8\">"
    "<TITLE>%s</TITLE></HEAD><BODY>%s</BODY></HTML>\n";

/* We may want these as config parameters someday, but we'll need to
 * address how to template in the authentication URL */
static const char *redir_title = "Authentication Required";
static const char *redir_body = 
        "<H1>Authentication Required</H1>"
        "Before proceeding, you must authenticate "
        "<A HREF=\"%s\">here</A>.";

void init_tcp_response_header(const tcp *tcp_stim, tcp *tcp_resp, 
        uint16_t payload_len, uint8_t flags);

static void ensure_default_properties(Properties *props);

Vlog_module lg("Http_redirector_component");

Http_redirector::Http_redirector(const container::Context* c,
                                 const json_object*) 
    : Component(c), ip_id(INITIAL_IPID), 
      resp_buf(raw_buf, sizeof(raw_buf))
{
    //NOP
}

void
Http_redirector::configure(const Configuration* conf) {
    //resolve required components
    resolve(storage);
    resolve(flow_util);
    
    //register for datapath join so we can insert a flow to ensure we
    //get the full HTTP packet at the Controller
    register_handler<Datapath_join_event>
            (boost::bind(&Http_redirector::handle_dp_join, this, _1));
}

void
Http_redirector::install() {
    //load our properties
    props = new Properties(storage, PROPERTIES_SECTION);
    ensure_default_properties(props);
    load_properties();

    if (!flow_util->fns.register_function(POLICY_FN_ID,
                                     boost::bind(&Http_redirector::redirect_http_request, this, _1)))
    {
        lg.err("Error registering policy function for '%s'", 
                POLICY_FN_ID.c_str());
    }
}

/*
 * Uses synchronous API - may only be called from install
 */
static void ensure_default_properties(Properties *props) {
    props->begin();
    Property_list_ptr pl = props->get_value(REDIR_URL_PROP);
    if (pl->size() == 0) {
        lg.warn("Initializing default property: '%s' => '%s'", 
                REDIR_URL_PROP.c_str(), REDIR_URL_DEFAULT.c_str());
        pl->push_back(Property(REDIR_URL_DEFAULT.c_str()));
    }
    pl = props->get_value(RST_UNAUTH_PKT_PROP);
    if (pl->size() == 0) {
        lg.warn("Initializing default property: '%s' => %"PRIx64, 
                RST_UNAUTH_PKT_PROP.c_str(), RST_UNAUTH_PKT_DEFAULT);
        pl->push_back(Property(RST_UNAUTH_PKT_DEFAULT));
    }
    props->commit();
}

static void add_callback_cb(const Properties::Callback_id id) {
    //NOP
}

static void add_callback_eb() {
    //NOP
}

void 
Http_redirector::props_load_eb() {
    lg.err("Error loading properties, component will be disabled");
    props_set = false;
    props->async_add_callback(
            boost::bind(&Http_redirector::load_properties, this),
            add_callback_cb, add_callback_eb);
}

void
Http_redirector::props_load_cb () {
    if ( props->get_value(RST_UNAUTH_PKT_PROP)->size() != 1 ||
         props->get_value(REDIR_URL_PROP)->size() != 1 ) {
        lg.warn("Missing required property, component will be disabled");
        props_set = false;
    }
    else {
        props_set = true;
    }

    if (props_set) {
        redir_payload_sz = get_redirect_payload(0).size();
        if (redir_payload_sz > MIN_SUPPORTED_MSS) {
            lg.warn("Redirect content exceeds recommended MSS; redirection "
                    "for devices with a MSS < %zu will fail",
                    redir_payload_sz);
        }
    }
    props->async_add_callback(
            boost::bind(&Http_redirector::load_properties, this),
            add_callback_cb, add_callback_eb);
}

void
Http_redirector::load_properties() {
    lg.dbg("Loading new properties");
    props->async_load(
            boost::bind(&Http_redirector::props_load_cb, this),
            boost::bind(&Http_redirector::props_load_eb, this));
}

Disposition
Http_redirector::handle_dp_join(const Event& e) {
    //insert a flow to ensure we get the full HTTP packet at the Controller
    const Datapath_join_event& dj = assert_cast<const Datapath_join_event&>(e);

    //TODO: add a corresponding flow for IPv6
    size_t size = sizeof(ofp_flow_mod) + sizeof(ofp_action_output);
    boost::shared_array<char> raw_of(new char[size]);
    ofp_flow_mod& ofm = *((ofp_flow_mod*) raw_of.get());

    ofm.header.version = OFP_VERSION;
    ofm.header.type = OFPT_FLOW_MOD;
    ofm.header.length = htons(size);
    ofm.header.xid = 0;

    ofm.match.wildcards = htonl(OFPFW_IN_PORT | OFPFW_DL_VLAN | OFPFW_DL_SRC | 
                                OFPFW_DL_DST | OFPFW_NW_SRC_MASK |
                                OFPFW_NW_DST_MASK | OFPFW_TP_SRC);
    ofm.match.dl_type = ethernet::IP;
    ofm.match.nw_proto = ip_::proto::TCP;
    ofm.match.tp_dst = htons(HTTP_PORT);

    ofm.command = htons(OFPFC_ADD);
    ofm.idle_timeout = htons(OFP_FLOW_PERMANENT);
    ofm.hard_timeout = htons(OFP_FLOW_PERMANENT);
    ofm.buffer_id = htonl(-1);
    ofm.priority = htons(10);
    ofm.reserved = 0;
    ofp_action_output& action = *((ofp_action_output*)ofm.actions);
    memset(&action, 0, sizeof(ofp_action_output));
    action.type = htons(OFPAT_OUTPUT);
    action.len = htons(sizeof(ofp_action_output));
    action.max_len = htons(0);
    action.port = htons(OFPP_CONTROLLER);

    int ret = send_openflow_command(dj.datapath_id, &ofm.header, true);
    if (ret) {
        lg.err("Error (%d) adding flow to dp '%s'; http request payload "
                "for automatic refresh may not be available", ret,
                dj.datapath_id.string().c_str());
    }
    else {
        lg.dbg("Flow added to dp '%s'; full matching packet payloads will be "
                "forwarded to the controller.", 
                dj.datapath_id.string().c_str());
    }
    return CONTINUE;
}

std::string
Http_redirector::get_redirect_payload(uint64_t cookie) {
    // Construct the date in RFC1123 format
    char tm_buf[30]; //date format yields deterministic length
    time_t rawtime;
    struct tm* tminfo;
    int date_len;
    char *global_locale = setlocale(LC_TIME, "POSIX");
    time(&rawtime);
    tminfo = gmtime(&rawtime);
    date_len = strftime(tm_buf, sizeof(tm_buf), "%a, %d %b %Y %H:%M:%S GMT", 
            tminfo);
    if (date_len == 0) {
        //this should not happen, but if it does, punt
        lg.err("HTTP Date header length exceeded the format specifications");
        tm_buf[0] = '\0';
    }
    setlocale(LC_TIME, global_locale);

    ostringstream hexcookie;
    hexcookie.flags(ios::hex);
    hexcookie.width(16);
    hexcookie.fill('0');
    hexcookie << cookie;
    Property_list_ptr plp = props->get_value(REDIR_URL_PROP);
    string redir_query = boost::get<string>((*plp)[0].get_value()) 
            + "?f=" + hexcookie.str();
    cout.unsetf(ios::hex);
    lg.dbg("Redirecting to '%s'", redir_query.c_str());

    // Construct the payload using current date and parameters from config
    string formatted_body = str(boost::format(redir_body) % redir_query);
    string payload = str(boost::format(redir_payload_fmt) % redir_title %
            formatted_body);
    string header = str(boost::format(redir_header_fmt) % redir_query % 
            payload.size() % tm_buf);

    return header + payload;
}

void
Http_redirector::redirect_http_request(const Flow_in_event &fi)
{
    if (!props_set) {
        lg.warn("Cannot redirect request: invalid configuration parameter(s)");
        return;
    }

    /*
     * Policy called us because in-band web auth is required for
     * communication, however we can't be sure that this is actually web
     * traffic 
     */
    if ((fi.flow.dl_type == ethernet::IP || fi.flow.dl_type == ethernet::IPV6)
        && fi.flow.nw_proto == ip_::proto::TCP)
    {
        // TODO: ipv6 won't actually work as not even flow supports it yet
        if (fi.flow.dl_type == ethernet::IPV6) {
            return;
        }

        /*
         * Parse the incoming packet to grab the TCP header
         *  - since the flow had a TCP type, we know we have full ETH,
         *    and at least partial IP
         */
        Buffer *in_buf = fi.buf.get();
        //assert(in_buf->size() > sizeof(ethernet));
        if (in_buf->size() < sizeof(ethernet)) {
            lg.err("Invalid packet size %zu - this shouldn't be possible",
                    in_buf->size());
            return;
        }
        ethernet* eth_stim = in_buf->pull<ethernet>();
        if (vlan::is_vlan(*eth_stim)) {
            assert(in_buf->size() > sizeof(vlan));
            in_buf->pull<vlan>();
        }
        //peek at the base ip header, to get the length
        const ip_ *ip_stim = in_buf->try_at<ip_>(0);
        if (ip_stim == NULL) {
            lg.err("Could not obtain base IP header; unable to redirect.");
            //this is the end of the policy chain, so returning results
            //in dropping the packet
            return;
        }
        int ip_len = ip_stim->ihl * 4;
        //remove ip header+opts from buffer, ignoring them
        if (in_buf->try_pull(ip_len) == NULL) {
            lg.err("Could not obtain IP header options; unable to redirect.");
            return;
        }
        //grab the base tcp header
        tcp *tcp_stim = in_buf->try_at<tcp>(0);
        if (tcp_stim == NULL) {
            lg.err("Could not obtain base TCP header; unable to redirect.");
            return;
        }
        uint16_t payload_len = ntohs(ip_stim->tot_len) - (ip_stim->ihl*4) -
                tcp_stim->len();
        uint16_t remaining_header_len = tcp_stim->data() - in_buf->data();
        uint16_t cap_payload_len = min((size_t)payload_len, in_buf->size() -
                remaining_header_len);
        if (tcp_stim->dport != htons(HTTP_PORT)) {
            Property_list_ptr plp = props->get_value(RST_UNAUTH_PKT_PROP);
            bool rst_unauth = bool(boost::get<int64_t>((*plp)[0].get_value()));
            if (rst_unauth) {
                ip_ *ip_resp = init_response_buffer(eth_stim);
                tcp *tcp_resp = (tcp*)ip_resp->data();
                ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                        sizeof(tcp)));
                init_tcp_response_header(tcp_stim, tcp_resp, 0, 
                        tcp::RST|tcp::ACK);
                tcp_resp->ack = htonl(ntohl(tcp_stim->seq) + 1);
                lg.dbg("Sending RST response to non TCP:%d traffic (TCP:%u)",
                        HTTP_PORT, ntohs(tcp_stim->dport));
                send_response_buffer(fi.datapath_id, fi.flow.in_port);
            }
            lg.dbg("Skipping TCP traffic to port %d (must be %d)",
                    ntohs(fi.flow.tp_dst), HTTP_PORT);
            return;
        }
        lg.dbg("Got a TCP/%d flow:'%s' flags:%d seq:%u ack:%u payload:%u "
               "captured_payload:%u", HTTP_PORT, fi.flow.to_string().c_str(), 
               tcp_stim->flags, ntohl(tcp_stim->seq), ntohl(tcp_stim->ack), 
               payload_len, cap_payload_len);

        /*
         * Respond to packet as appropriate
         */
        if (tcp_stim->flags & tcp::RST) {
            lg.dbg("Dropping RST for flow '%s flags %d'", 
                    fi.flow.to_string().c_str(), tcp_stim->flags);
            return; //NOP
        }
        else if (tcp_stim->flags == tcp::SYN) {
            /*
             * respond to SYN with SYN/ACK 
             *   our ISN = (peer_ISN << 16 & 0xFF00)
             */
            ip_ *ip_resp = init_response_buffer(eth_stim);
            tcp *tcp_resp = (tcp*)ip_resp->data();
            ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + sizeof(tcp)));
            init_tcp_response_header(tcp_stim, tcp_resp, 0, tcp::SYN|tcp::ACK);
            tcp_resp->seq = htonl(ntohl(tcp_stim->seq) << 16);
            tcp_resp->ack = htonl(ntohl(tcp_stim->seq) + 1);

            lg.dbg("Sending SYN/ACK (S=%u A=%u) response to SYN (s=%u)",
                    ntohl(tcp_resp->seq), ntohl(tcp_resp->ack), 
                    ntohl(tcp_stim->seq));
            send_response_buffer(fi.datapath_id, fi.flow.in_port);
            return;
        }

        /*
         * It appears that a session is in progress.  Decode ACK # into 
         * bytes sent and bytes acknowledged.
         */
        uint16_t bytes_acknowledged = uint16_t(ntohl(tcp_stim->ack));
        uint16_t bytes_from_peer = uint16_t(ntohl(tcp_stim->seq)) -
                uint16_t(ntohl(tcp_stim->ack) >> 16);
        lg.dbg("Peer has acknowledged %u bytes and has sent %u bytes payload "
                "is %d",
                bytes_acknowledged, bytes_from_peer, payload_len);

        if (tcp_stim->flags == tcp::ACK && bytes_from_peer == 1 &&
                payload_len == 0)
        {
            //just ending 3 way handshake - ignore it
            lg.dbg("Received ACK with no data, ignoring");
            return;
        }
        else if (tcp_stim->flags & tcp::ACK) {
            if (bytes_from_peer > MAX_QUERY_LEN) {
                ip_ *ip_resp = init_response_buffer(eth_stim);
                tcp *tcp_resp = (tcp*)ip_resp->data();
                ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                        sizeof(tcp)));
                init_tcp_response_header(tcp_stim, tcp_resp, payload_len, 
                        tcp::RST|tcp::ACK);
                lg.dbg("Sending RST response to ACK after %u bytes "
                        "received from us and %u bytes sent",
                        bytes_acknowledged, bytes_from_peer);
                send_response_buffer(fi.datapath_id, fi.flow.in_port);
                return;
            }
            if (payload_len > 0) {
                if (cap_payload_len < payload_len) {
                    lg.warn("Truncated payload passed to http_redirect; "
                            "automatic redirection may not be possible.");
                }
                //Cache the flow so we know what we will authenticate
                rd_flow_cache.update_redirected_flow(fi.flow, fi.datapath_id,
                        tcp_stim->data(), bytes_from_peer - 1, cap_payload_len);

                //ACK the received data
                ip_ *ip_resp = init_response_buffer(eth_stim);
                tcp *tcp_resp = (tcp*)ip_resp->data();
                ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                            sizeof(tcp)));
                init_tcp_response_header(tcp_stim, tcp_resp, payload_len, 
                        tcp::ACK);
                lg.dbg("Sending ACK (S=%u A=%u) in response to ACK w/ payload "
                        "from peer after %u bytes received from us and %u "
                        "bytes sent (our payload is %zu)", 
                        ntohl(tcp_resp->seq), ntohl(tcp_resp->ack),
                        bytes_acknowledged, bytes_from_peer + payload_len,
                        redir_payload_sz);
                send_response_buffer(fi.datapath_id, fi.flow.in_port);
            }
            else {
                lg.dbg("Ignoring ACK from peer with no payload "
                        "after %u bytes received from us and %u "
                        "bytes sent (our payload is %zu)", 
                        bytes_acknowledged, bytes_from_peer + payload_len,
                        redir_payload_sz);
            }

            //see if we need to send our payload
            if (bytes_from_peer + payload_len > 1) {
                ip_ *ip_resp = init_response_buffer(eth_stim);
                tcp *tcp_resp = (tcp*)ip_resp->data();
                //they've sent data, assume it's a properly formed GET request
                //TODO: perhaps we only want to send response after we
                //receive 0d 0a 0d 0a (or 0a 0d{0,1} 0a) ...?
                if (bytes_acknowledged < redir_payload_sz + 1) {
                    //they haven't received entire payload, send it
                    ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                            sizeof(tcp)) + redir_payload_sz);
                    init_tcp_response_header(tcp_stim, tcp_resp, payload_len,
                            tcp::PUSH|tcp::ACK);
                    uint64_t fid = Redirected_flow::get_id_for_flow(fi.flow,
                            fi.datapath_id);
                    get_redirect_payload(fid).copy((char*)tcp_resp->data(),
                            redir_payload_sz);
                    lg.dbg("Sending ACK w/ payload (S=%u A=%u) in response "
                            "to ACK after %u bytes received from us and %u "
                            "bytes sent (our payload is %zu)", 
                            ntohl(tcp_resp->seq), ntohl(tcp_resp->ack),
                            bytes_acknowledged, bytes_from_peer + payload_len,
                            redir_payload_sz);
                }
                else if (bytes_acknowledged == redir_payload_sz + 1) {
                    //they've gotten our payload, need to FIN
                    ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                                sizeof(tcp)));
                    init_tcp_response_header(tcp_stim, tcp_resp, payload_len,
                            tcp::FIN|tcp::ACK);
                    lg.dbg("Sending FIN/ACK (S=%u A=%u) in response to "
                            "ACK after %u bytes received from us and "
                            "%u bytes sent (our payload is %zu)", 
                            ntohl(tcp_resp->seq), ntohl(tcp_resp->ack),
                            bytes_acknowledged, bytes_from_peer + 
                            payload_len, redir_payload_sz);
                }
                else if (bytes_acknowledged == redir_payload_sz + 2) {
                    if (tcp_stim->flags & tcp::FIN) {
                        //they're completing the shutdown
                        ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                                sizeof(tcp)));
                        init_tcp_response_header(tcp_stim, tcp_resp, 
                                payload_len, tcp::ACK);
                        lg.dbg("Sending ACK (S=%u A=%u) in response to "
                                "FIN/ACK after %u bytes received from us and "
                                "%u bytes sent (our payload is %zu)", 
                                ntohl(tcp_resp->seq), ntohl(tcp_resp->ack),
                                bytes_acknowledged, bytes_from_peer + 
                                payload_len, redir_payload_sz);
                    }
                    else {
                        //they've gotten our payload, and FIN, and we've
                        //already ACKed, nothing to do
                        //drop the packet
                        return;
                    }
                }
                else {
                    //how'd they get so much data?
                    lg.dbg("Sending RST response to ACK after %u bytes "
                            "received from us (our payload is %zu)", 
                            bytes_acknowledged, redir_payload_sz);
                    ip_resp->tot_len = htons(uint16_t(sizeof(ip_) + 
                            sizeof(tcp)));
                    init_tcp_response_header(tcp_stim, tcp_resp, payload_len, 
                            tcp::RST|tcp::ACK);
                }
                send_response_buffer(fi.datapath_id, fi.flow.in_port);
            }
        }
        else {
            // else drop
            lg.dbg("Dropping flow '%s'", fi.flow.to_string().c_str());
        }
    }
    else {
        lg.dbg("Skipping non IP/TCP traffic: %d:%d",
                fi.flow.nw_proto, fi.flow.tp_dst);
    }
}

/*
 * send_response_buffer - calculate checksums, trim buffer, and send
 */
void
Http_redirector::send_response_buffer(datapathid datapath_id, 
        uint16_t in_port)
{
    // Determine the size of the packet and trim the buffer
    ethernet *eth = (ethernet*)resp_buf.data();
    //TODO: IPv6
    ip_ *iph;
    if (vlan::is_vlan(*eth)) {
        iph= (ip_*)((((vlan*)(eth->data())))->data());
    }
    else {
        iph = (ip_*)(eth->data());
    }
    resp_buf.trim(ethernet::ETHER_LEN + 
            (vlan::is_vlan(*eth) ? sizeof(vlan) : 0) +
            ntohs(iph->tot_len));

    // Update the checksums
    iph->csum = iph->calc_csum();
    ((tcp*)(iph->data()))->check = 
            tcp::checksum(iph->saddr, iph->daddr, ((tcp*)(iph->data())), 
            ntohs(iph->tot_len) - iph->ihl*4);

    // We send without blocking or checking result, if send fails, we
    // rely on peer's TCP stack to resend request
    lg.dbg("Sending packet of size %zu", resp_buf.size());
    send_openflow_packet(datapath_id, resp_buf, ntohs(in_port), 
            OFPP_CONTROLLER, false);
}

/*
 * init_response_buffer - init ethernet, vlan, and ip header as response
 *                        to eth_stim
 */
ip_*
Http_redirector::init_response_buffer(ethernet *eth_stim) {
    resp_buf.reinit(raw_buf, sizeof(raw_buf));
    ip_ *ip_stim;
    ip_ *ip_resp;
    ethernet *eth_resp = (ethernet*)resp_buf.data();
    eth_resp->saddr = eth_stim->daddr;
    eth_resp->daddr = eth_stim->saddr;
    eth_resp->type = eth_stim->type;
    if (vlan::is_vlan(*eth_stim)) {
        vlan *vlan_stim = (vlan*)eth_stim->data();
        vlan *vlan_resp = (vlan*)eth_resp->data();
        vlan_resp->set_id(vlan_stim->id());
        vlan_resp->encapsulated_proto = vlan_stim->encapsulated_proto;
        ip_stim = (ip_ *)vlan_stim->data();
        ip_resp = (ip_ *)vlan_resp->data();
    } else {
        ip_stim = (ip_ *)eth_stim->data();
        ip_resp = (ip_ *)eth_resp->data();
    }

    ip_resp->ihl = 5;
    ip_resp->ver = 4;
    ip_resp->tos = 0;
    ip_resp->tot_len = 0;
    ip_resp->id = htons(ip_id++);
    ip_resp->frag_off = 0;
    ip_resp->ttl = ip_::DEFTTL;
    ip_resp->protocol = ip_::proto::TCP;
    ip_resp->csum = 0;
    ip_resp->saddr = ip_stim->daddr;
    ip_resp->daddr = ip_stim->saddr;
    return ip_resp;
}

void
Http_redirector::getInstance(const container::Context* ctxt,
                            Http_redirector*& h) {
    h = dynamic_cast<Http_redirector*>
        (ctxt->get_by_interface(container::Interface_description
                              (typeid(Http_redirector).name())));
}

/*
 * init_tcp_response_header - init data in tcp_resp as response to tcp_stim
 */
void
init_tcp_response_header(const tcp *tcp_stim, tcp *tcp_resp, 
        u_int16_t payload_len, uint8_t flags)
{
    tcp_resp->sport = tcp_stim->dport;
    tcp_resp->dport = tcp_stim->sport;

    tcp_resp->seq = tcp_stim->ack;
    tcp_resp->ack = htonl(ntohl(tcp_stim->seq) + payload_len +
            (tcp_stim->flags & tcp::FIN ? 1 : 0));
    tcp_resp->off = 5;
    tcp_resp->flags = flags;
    tcp_resp->win = htons(TCP_WIN);
    tcp_resp->check = 0;
    tcp_resp->urp = 0;
}

} // namespace applications
} // namespace vigil

REGISTER_COMPONENT(container::Simple_component_factory<Http_redirector>, 
                   Http_redirector);


