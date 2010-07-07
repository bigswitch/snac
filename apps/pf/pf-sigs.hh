/*
 */

#ifndef PF_SIGS_HH
#define PF_SIGS_HH

#include <string>
#include <vector>

#include "pf-match.hh"

extern "C"
{
#include <stdint.h>
}

namespace vigil {
namespace applications {

typedef struct tcpopt {
  enum { OPT_NONE, OPT_M, OPT_MMOD, OPT_MSTAR, OPT_N,
	 OPT_T, OPT_T0, OPT_S, OPT_W, OPT_WMOD, OPT_WSTAR } o_type;
  uint32_t o_val;
} tcpopt_t;

typedef struct osdat {
  char *od_name;
  enum { WIN_ANY, WIN_EQ, WIN_MOD, WIN_S, WIN_T } od_wintype;
  uint32_t od_win;
  uint32_t od_ttl;
  int od_df;
  int od_size;
  std::vector<tcpopt_t> vod_opts;
} osdat_t;

typedef struct fpdat {
  uint32_t fp_win;
  uint32_t fp_ttl;
  int fp_df;
  int fp_size;
  std::vector<tcpopt_t> vfp_opts;
} fpdat_t;

struct pf_sigs
{
    std::vector<osdat_t> vos;
    static const unsigned int synos_mtu = 1500;

private:
    int  parseos (osdat_t *odp, const char *line);
    int  parsefp (fpdat_t *fpp, const char *fps);
    int  lookup (const char *fps, std::string& str);
    int  check (const fpdat_t *fpp, const osdat_t *odp);

public:    
    int load_config (const std::string& osfile);
    int parse       (uint8_t *buf, int size, pf_match& matchout);

    int numsigs(){
        return vos.size();
    }
};

}
}
#endif  // -- PF_SIGS_HH
