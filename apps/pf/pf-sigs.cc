/* Derived from OpenBSD pf
 */

#include "pf-sigs.hh"
#include "netinet++/ethernet.hh"

#include <iostream>
#include <fstream>
#include <vector>
#include <cstdlib>

#include "vlog.hh"

extern "C"
{
#include <malloc.h>
#include <string.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <netinet/in_systm.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/in.h>
#include <arpa/inet.h>
}

using namespace std;
using namespace vigil;
using namespace vigil::applications;

#define getshort(s) (uint16_t)( ((uint8_t)*(s) << 8) + ((uint8_t)*((s)+1)) )
#define getint(s)   (uint32_t)( (((uint8_t)*(s) << 24)  + ((uint8_t)*((s)+1) << 16)) +\
                                (((uint8_t)*((s)+2) << 8) + ((uint8_t)*((s)+3))) )

static Vlog_module lg("bpf");

int 
pf_sigs::parse (uint8_t *buf, int size, pf_match& matchout)
{
    char fp[128];
    const u_char *e = buf + size;

    ethernet* ethh = (ethernet*)buf; 
    const u_char *ip =  0;
    if (ethh->type == ethernet::VLAN){
        ip = buf + 18;
    }else{
        ip = buf + 14;
    }

    const u_char *tcp = ip + ((ip[0] & 0xf) << 2);
    if (tcp + 20 > e){
        lg.warn(" pf-sigs packet too small tcp\n");
        return -1;
    }

    sprintf (fp, "%d:%d:%d:%d:", 
            getshort (tcp + 14), ip[8],
            !!(ip[6] & 0x40), getshort (ip + 2));

    const u_char *op = tcp + 20;
    const char *sep = "";
    char tmp[256];

    while (op < e) {
        if (*op > 1 && (op + 2 > e || op + op[1] > e || op[1] < 2))
            goto done;
        switch (*op) {
            case 0:
                goto done;
            case 1:
                sprintf(tmp,"%sN",sep);
                strcat(fp, tmp);
                sep = ",";
                op++;
                continue;
            case 2:
                if (op[1] != 4)
                    goto done;
                sprintf (tmp, "%sM%d", sep, getshort (op + 2));
                strcat(fp, tmp);
                sep = ",";
                break;
            case 3:
                if (op[1] != 3)
                    goto done;
                sprintf (tmp, "%sW%d", sep, op[2]);
                strcat(fp, tmp);
                sep = ",";
                break;
            case 4:
                if (op[1] != 2)
                    goto done;
                sprintf(tmp,"%sS",sep);
                strcat(fp, tmp);
                sep = ",";
                break;
            case 8:
                if (op[1] != 10)
                    goto done;
                sprintf(tmp,"%sT",sep);
                strcat(fp, tmp);

                if (!getint (op + 2)) {
                    strcat(fp, "0");
                }
                sep = ",";
                break;
        }
        op += op[1];
    }

done:
    matchout.signature = (char*)fp;
    return lookup(fp, matchout.os);
}

int  
pf_sigs::load_config (const std::string& osfile)
{
    osdat_t os;
    int line = 0;

    ::memset (&os, 0, sizeof (os));

    ifstream ifs;
    ifs.open(osfile.c_str());
    if(!ifs){
        lg.warn("pf_sigs::load_config error opening %s\n", osfile.c_str());
        return -1;
    }

    vos.clear();

    string str;
    getline(ifs, str);

    while (ifs){
        vos.push_back(os);
        int r = parseos (&vos.back(), str.c_str());

        line++;
        getline(ifs, str);
        if (r < 0){
            continue;
        } else if (r == 0) {
            lg.err("%s:%d: syntax error\n", osfile.c_str(), line);
            continue;
        }
    }

    return 0;
}

int
pf_sigs::lookup (const char *fps, std::string& str)
{
    fpdat_t fp;
    osdat_t os;

    memset (&fp, 0, sizeof (fp));

    if (!parsefp (&fp, fps)) {
        lg.dbg("pf_sigs::lookup: bad fingerprint %s\n",fps);
        return -1;
    }

    for (size_t i = 0; i < vos.size(); ++i) {
        if (check (&fp, &vos[i])) {
            str = (vos[i].od_name);
            return 1;
        }
    }

    str = "unknown";
    return 0;
}

int
pf_sigs::parseos (osdat_t *odp, const char *line)
{
    int n;
    const char *s = line;
    int begin = 1;

    if (!*s || *s == '#' || *s == '\n')
        return -1;

    odp->vod_opts.clear();
    ::free (odp->od_name);
    odp->od_name = NULL;

    if (*s == '*') {
        odp->od_wintype = osdat::WIN_ANY;
        s++;
    }
    else {
        if (*s == '%')
            odp->od_wintype = osdat::WIN_MOD;
        else if (*s == 'S')
            odp->od_wintype = osdat::WIN_S;
        else if (*s == 'T')
            odp->od_wintype = osdat::WIN_T;
        else {
            odp->od_wintype = osdat::WIN_EQ;
            s--;
        }
        s++;
        if (sscanf (s, "%u%n", &odp->od_win, &n) != 1)
            return 0;
        s += n;
    }

    if (sscanf (s, ":%u:%d:%d:%n", &odp->od_ttl,
                &odp->od_df, &odp->od_size, &n) != 3)
        return 0;
    s += n - 1;

    for (;;) {

        tcpopt_t opp;

        if (!*s)
            return 0;
        if (*s == ':' && !begin)
            break;
        if (*s != ':' && *s != ',')
            return 0;
        s++;
        if (begin && *s == '.') {
            s++;
            break;
        }
        begin = 0;


        switch (*s++) {
            case 'N':
                opp.o_type = tcpopt::OPT_N;
                break;
            case 'W':
                if (*s == '*') {
                    s++;
                    opp.o_type = tcpopt::OPT_WSTAR;
                    break;
                }
                if (*s == '%') {
                    opp.o_type = tcpopt::OPT_WMOD;
                    s++;
                }
                else
                    opp.o_type = tcpopt::OPT_W;
                if (sscanf (s, "%u%n", &opp.o_val, &n) != 1)
                    return 0;
                s += n;
                break;
            case 'M':
                if (*s == '*') {
                    s++;
                    opp.o_type = tcpopt::OPT_MSTAR;
                    break;
                }
                if (*s == '%') {
                    opp.o_type = tcpopt::OPT_MMOD;
                    s++;
                }
                else
                    opp.o_type = tcpopt::OPT_M;
                if (sscanf (s, "%u%n", &opp.o_val, &n) != 1)
                    return 0;
                s += n;
                break;
            case 'S':
                opp.o_type = tcpopt::OPT_S;
                break;
            case 'T':
                if (*s == '0') {
                    opp.o_type = tcpopt::OPT_T0;
                    s++;
                }
                else
                    opp.o_type = tcpopt::OPT_T;
                break;
            default:
                return 0;
        }
        odp->vod_opts.push_back(opp);
    }

    if ((s = strrchr (s, ':'))) {
        odp->od_name = strdup (s + 1);
        n = strlen (odp->od_name);
        if (n > 0 && odp->od_name[n - 1] == '\n')
            odp->od_name[n - 1] = '\0';
        return 1;
    }

    return 0;
}

int
pf_sigs::parsefp (fpdat_t *fpp, const char *fps)
{
    int n;
    const char *s = fps;

    fpp->vfp_opts.clear();

    if (sscanf (s, "%u:%u:%d:%d%n", &fpp->fp_win, &fpp->fp_ttl,
                &fpp->fp_df, &fpp->fp_size, &n) != 4)
        return 0;
    s += n;

    for (;;) {
        tcpopt_t opp;

        if (!*s)
            return 1;
        if (*s != ':' && *s != ',')
            return 0;

        s++;


        switch (*s++) {
            case 'N':
                opp.o_type = tcpopt::OPT_N;
                break;
            case 'W':
                if (sscanf (s, "%u%n", &opp.o_val, &n) != 1)
                    return 0;
                opp.o_type = tcpopt::OPT_W;
                s += n;
                break;
            case 'M':
                if (sscanf (s, "%u%n", &opp.o_val, &n) != 1)
                    return 0;
                opp.o_type = tcpopt::OPT_M;
                s += n;
                break;
            case 'S':
                opp.o_type = tcpopt::OPT_S;
                break;
            case 'T':
                if (*s == '0') {
                    opp.o_type = tcpopt::OPT_T0;
                    s++;
                }
                else
                    opp.o_type = tcpopt::OPT_T;
                break;
            default:
                return 0;
        }

        fpp->vfp_opts.push_back(opp);
    }
}

int
pf_sigs::check (const fpdat_t *fpp, const osdat_t *odp)
{
    size_t i;
    uint32_t mss = 0;
    int mss_valid = 0;

    if (fpp->fp_ttl > odp->od_ttl || fpp->fp_ttl + 40 < odp->od_ttl)
        return 0;
    if (fpp->fp_df != odp->od_df)
        return 0;
    if (fpp->fp_size != odp->od_size)
        return 0;

    if(fpp->vfp_opts.size() != odp->vod_opts.size())
        return 0;

    for (i = 0; i < fpp->vfp_opts.size(); i++) {
        switch (odp->vod_opts[i].o_type) {
            case tcpopt::OPT_M:
                if (fpp->vfp_opts[i].o_type != tcpopt::OPT_M)
                    return 0;
                mss = fpp->vfp_opts[i].o_val;
                mss_valid = 1;
                if (mss != odp->vod_opts[i].o_val)
                    return 0;
                break;
            case tcpopt::OPT_MMOD:
                if (fpp->vfp_opts[i].o_type != tcpopt::OPT_M)
                    return 0;
                mss = fpp->vfp_opts[i].o_val;
                mss_valid = 1;
                if (mss % odp->vod_opts[i].o_val)
                    return 0;
                break;
            case tcpopt::OPT_MSTAR:
                if (fpp->vfp_opts[i].o_type != tcpopt::OPT_M)
                    return 0;
                mss = fpp->vfp_opts[i].o_val;
                mss_valid = 1;
                break;
            default:
                if (odp->vod_opts[i].o_type != fpp->vfp_opts[i].o_type)
                    return 0;
                break;
        }
    }

    switch (odp->od_wintype) {
        case osdat::WIN_ANY:
            break;
        case osdat::WIN_EQ:
            if (fpp->fp_win != odp->od_win)
                return 0;
            break;
        case osdat::WIN_S:
            if ((!synos_mtu || fpp->fp_win != odp->od_win * (synos_mtu - 40))
                    && (!mss_valid || fpp->fp_win != odp->od_win * mss))
                return 0;
            break;
        case osdat::WIN_T:
            if ((!synos_mtu || fpp->fp_win != odp->od_win * synos_mtu)
                    && (!mss_valid || fpp->fp_win != odp->od_win * (mss + 40)))
                return 0;
        case osdat::WIN_MOD:
            if (fpp->fp_win % odp->od_win)
                return 0;
            break;
    }

    return 1;
}
