/* Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */
#ifndef LISTENER_HH
#define LISTENER_HH 1

#include <list>

#include <boost/bind.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/shared_ptr.hpp>

#include "tcp-socket.hh"
#include "threads/cooperative.hh"

namespace vigil { 

/*
 * Listener component for inbound TCP connections.
 */
template <typename T>
class Listener 
    : public Co_thread {
public:
    //void servant_exit(const boost::shared_ptr<T>&) {
    //}
    
    void init(int port, int backlog) {
        ssocket.set_reuseaddr();
        int error = ssocket.bind(INADDR_ANY, htons(port));
        if (error) {
            throw std::runtime_error(std::string("Unable to bind to port ") + 
                                     boost::lexical_cast<std::string>(port));
        }
        
        error = ssocket.listen(backlog);
        if (error) {
            throw std::runtime_error(std::string("Unable to listen to port ") + 
                                     boost::lexical_cast<std::string>(port) + 
                                     " (backlog = " + 
                                     boost::lexical_cast<std::string>(port) + 
                                     ")");
        }
    }

    virtual boost::shared_ptr<T> get_servant(std::auto_ptr<Tcp_socket>) = 0;

    /* Forks a thread per a TCP connection. */
    void run() {
        for (;;) {
            int error;
            ssocket.accept_wait();
            co_block();
            std::auto_ptr<Tcp_socket> new_socket = ssocket.accept(error, true);
            if (error) {
                if (error != EAGAIN) {
                    //lg.err("Listener accept error: %d", error);
                }
                continue;
            }
            
            boost::shared_ptr<T> servant = get_servant(new_socket);
            //servants.push_back(servant);
            servant->start(boost::bind(&T::run, servant));
        }
    }
    
private:

    /* Pointers to all currently running servants */ 
    //std::list<boost::shared_ptr<T> > servants;

    /* Listening socket */
    Tcp_socket ssocket;
};

}

#endif
