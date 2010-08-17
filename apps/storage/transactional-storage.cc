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

#include "transactional-storage.hh"

using namespace vigil;
using namespace vigil::applications::storage;

Async_transactional_storage::~Async_transactional_storage() {

} 

void 
Async_transactional_storage::getInstance(const container::Context* ctxt, 
                                         Async_transactional_storage*& s) {
    s = dynamic_cast<Async_transactional_storage*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(Async_transactional_storage).name())));
}

Async_transactional_connection::~Async_transactional_connection() {

}

Async_transactional_cursor::~Async_transactional_cursor() {

}

