%module pypf

%{
#include "pypf.cc"

#include "pf.hh"
#include "buffer.hh"
#include "pypf.hh"
using namespace vigil;
%}

%include "std_string.i"
%include "buffer.i"

struct pf_match
{
    std::string os;
    std::string signature;
};

struct p0f_match
{
    std::string os;
    std::string os_desc;
    std::string signature;
    std::string link_type;

    bool wss_mss_missmatch; // for NAT detection 
    bool ecn;
    bool df_missmatch; // may indicate firewall 

    bool filled;

    unsigned int timestamp;
    int isn;

    int ttl_distance; // OS default ttl - ttl

    p0f_match();
};

struct pf_results
{
    p0f_match p0f; 
    pf_match  bpf;
};

class PyPF {
public:
    PyPF(PyObject*);

    void configure(PyObject*);
    void install();

    PyObject* get_all_fingerprints(); // for debugging 
    bool get_fingerprints(ethernetaddr& eth, ipaddr& ipa, pf_results&);
};
    
/* Rewrite the high level interface to set_transform */
%pythoncode
%{
    import array
    def getFactory():
        class Factory:
            def instance(self, context):
                class PF:
                    def __init__(self, c):
                        self.pf = PyPF(c)
    
                    def configure(self, configuration):
                        self.pf.configure(configuration)

                    def install(self):
                        self.pf.install()

                    def getInterface(self):
                        return str(PyPF)

                    def get_fingerprints(self, eth, ip, results):
                        return self.pf.get_fingerprints(eth, ip,results)

                    def get_all_fingerprints(self):
                        return self.pf.get_all_fingerprints()

                return PF(context)
        return Factory()
%}
