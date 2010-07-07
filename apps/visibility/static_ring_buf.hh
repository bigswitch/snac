/*
 * Copyright 2008 (C) Nicira, Inc.
 */
#ifndef STATIC_RING_BUF_HH
#define STATIC_RING_BUF_HH

#include <sys/time.h>
#include <stdio.h>
#include <deque>

using namespace std;

/*
 * Static_ring_buf - a statically allocated ring buffer optimized for puts
 *
 * Optimized for buffers that are expected to be full much of their lives
 *
 * Tests indicate 'put' op is approximately 5X faster than an STL deque
 * based implemenation
 *
 */
template <class T>
class Static_ring_buf {
    public:
    typedef T element_type;

    Static_ring_buf(size_t sz)
       : buf(new element_type[sz]), max_sz(sz), cur_sz(0), head(0), tail(0)
    {
        //NOP
    }

    ~Static_ring_buf() {
        delete [] buf;
    }

    void put(element_type item) {
        buf[tail] = item;
        if (tail == max_sz-1) {
            tail = 0;
        }
        else {
            ++tail;
        }
        if (cur_sz < max_sz) {
            ++cur_sz;
        }
        else {
            head = tail;
        }
    }

    element_type get(size_t index) const {
        size_t bufidx = (head + index) % max_sz;
        return buf[bufidx];
    }

    inline size_t size() const {
        return cur_sz;
    }

    private:
    element_type *buf;
    size_t max_sz, cur_sz;
    size_t head, tail;
};

#endif /* STATIC_RING_BUF_HH */
