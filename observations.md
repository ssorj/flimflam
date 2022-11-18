# Observations

## pn_raw_connection_give_read_buffers

Slow case:

~~~ c
     279      623073 : size_t pn_raw_connection_give_read_buffers(pn_raw_connection_t *conn, pn_raw_buffer_t const *buffers, size_t num) {
     280      623073 :   assert(conn);
     281      623073 :   size_t can_take = pn_min(num, pn_raw_connection_read_buffers_capacity(conn));
     282      622842 :   if ( can_take==0 ) return 0;
     283             :
     284      622842 :   buff_ptr current = conn->rbuffer_first_empty;
     285      622842 :   assert(current);
     286             :
     287             :   buff_ptr previous;
     288     1245751 :   for (size_t i = 0; i < can_take; i++) {
     289             :     // Get next free
     290      622909 :     assert(conn->rbuffers[current-1].type == buff_rempty);
     291      622909 :     conn->rbuffers[current-1].context = buffers[i].context;
     292      622909 :     conn->rbuffers[current-1].bytes = buffers[i].bytes;
     293      622909 :     conn->rbuffers[current-1].capacity = buffers[i].capacity;
     294      622909 :     conn->rbuffers[current-1].size = 0;
     295      622909 :     conn->rbuffers[current-1].offset = buffers[i].offset;
     296      622909 :     conn->rbuffers[current-1].type = buff_unread;
     297             :
     298      622909 :     previous = current;
     299      622909 :     current = conn->rbuffers[current-1].next;
     300             :   }
     301      622842 :   if (!conn->rbuffer_last_unused) {
     302           5 :     conn->rbuffer_last_unused = previous;
     303             :   }
     304             :
     305      622842 :   conn->rbuffers[previous-1].next = conn->rbuffer_first_unused;
     306      622842 :   conn->rbuffer_first_unused = conn->rbuffer_first_empty;
     307      622842 :   conn->rbuffer_first_empty = current;
     308             :
     309      622842 :   conn->rbuffer_count += can_take;
     310      622842 :   conn->rrequestedbuffers = false;
     311      622842 :   return can_take;
     312             : }
~~~

Fast case:

~~~ c
     279      761061 : size_t pn_raw_connection_give_read_buffers(pn_raw_connection_t *conn, pn_raw_buffer_t const *buffers, size_t num) {
     280      761061 :   assert(conn);
     281      761061 :   size_t can_take = pn_min(num, pn_raw_connection_read_buffers_capacity(conn));
     282      760436 :   if ( can_take==0 ) return 0;
     283             :
     284      760436 :   buff_ptr current = conn->rbuffer_first_empty;
     285      760436 :   assert(current);
     286             :
     287             :   buff_ptr previous;
     288     3796225 :   for (size_t i = 0; i < can_take; i++) {
     289             :     // Get next free
     290     3035789 :     assert(conn->rbuffers[current-1].type == buff_rempty);
     291     3035789 :     conn->rbuffers[current-1].context = buffers[i].context;
     292     3035789 :     conn->rbuffers[current-1].bytes = buffers[i].bytes;
     293     3035789 :     conn->rbuffers[current-1].capacity = buffers[i].capacity;
     294     3035789 :     conn->rbuffers[current-1].size = 0;
     295     3035789 :     conn->rbuffers[current-1].offset = buffers[i].offset;
     296     3035789 :     conn->rbuffers[current-1].type = buff_unread;
     297             :
     298     3035789 :     previous = current;
     299     3035789 :     current = conn->rbuffers[current-1].next;
     300             :   }
     301      760436 :   if (!conn->rbuffer_last_unused) {
     302      189732 :     conn->rbuffer_last_unused = previous;
     303             :   }
     304             :
     305      760436 :   conn->rbuffers[previous-1].next = conn->rbuffer_first_unused;
     306      760436 :   conn->rbuffer_first_unused = conn->rbuffer_first_empty;
     307      760436 :   conn->rbuffer_first_empty = current;
     308             :
     309      760436 :   conn->rbuffer_count += can_take;
     310      760436 :   conn->rrequestedbuffers = false;
     311      760436 :   return can_take;
     312             : }
~~~

## pn_raw_connection_write_buffers

Slow case:

~~~ c
     347      623388 : size_t pn_raw_connection_write_buffers(pn_raw_connection_t *conn, pn_raw_buffer_t const *buffers, size_t num) {
     348      623388 :   assert(conn);
     349      623388 :   size_t can_take = pn_min(num, pn_raw_connection_write_buffers_capacity(conn));
     350      623323 :   if ( can_take==0 ) return 0;
     351             :
     352      623323 :   buff_ptr current = conn->wbuffer_first_empty;
     353      623323 :   assert(current);
     354             :
     355             :   buff_ptr previous;
     356     1246627 :   for (size_t i = 0; i < can_take; i++) {
     357             :     // Get next free
     358      623304 :     assert(conn->wbuffers[current-1].type == buff_wempty);
     359      623304 :     conn->wbuffers[current-1].context = buffers[i].context;
     360      623304 :     conn->wbuffers[current-1].bytes = buffers[i].bytes;
     361      623304 :     conn->wbuffers[current-1].capacity = buffers[i].capacity;
     362      623304 :     conn->wbuffers[current-1].size = buffers[i].size;
     363      623304 :     conn->wbuffers[current-1].offset = buffers[i].offset;
     364      623304 :     conn->wbuffers[current-1].type = buff_unwritten;
     365             :
     366      623304 :     previous = current;
     367      623304 :     current = conn->wbuffers[current-1].next;
     368             :   }
     369             :
     370      623323 :   if (!conn->wbuffer_first_towrite) {
     371      623309 :     conn->wbuffer_first_towrite = conn->wbuffer_first_empty;
     372             :   }
     373      623323 :   if (conn->wbuffer_last_towrite) {
     374           0 :     conn->wbuffers[conn->wbuffer_last_towrite-1].next = conn->wbuffer_first_empty;
     375             :   }
     376             :
     377      623323 :   conn->wbuffer_last_towrite = previous;
     378      623323 :   conn->wbuffers[previous-1].next = 0;
     379      623323 :   conn->wbuffer_first_empty = current;
     380             :
     381      623323 :   conn->wbuffer_count += can_take;
     382      623323 :   conn->wrequestedbuffers = false;
     383      623323 :   return can_take;
     384             : }
~~~

Fast case:

~~~ c
     347     1524489 : size_t pn_raw_connection_write_buffers(pn_raw_connection_t *conn, pn_raw_buffer_t const *buffers, size_t num) {
     348     1524489 :   assert(conn);
     349     1524489 :   size_t can_take = pn_min(num, pn_raw_connection_write_buffers_capacity(conn));
     350     1523253 :   if ( can_take==0 ) return 0;
     351             :
     352     1523253 :   buff_ptr current = conn->wbuffer_first_empty;
     353     1523253 :   assert(current);
     354             :
     355             :   buff_ptr previous;
     356     4739155 :   for (size_t i = 0; i < can_take; i++) {
     357             :     // Get next free
     358     3215902 :     assert(conn->wbuffers[current-1].type == buff_wempty);
     359     3215902 :     conn->wbuffers[current-1].context = buffers[i].context;
     360     3215902 :     conn->wbuffers[current-1].bytes = buffers[i].bytes;
     361     3215902 :     conn->wbuffers[current-1].capacity = buffers[i].capacity;
     362     3215902 :     conn->wbuffers[current-1].size = buffers[i].size;
     363     3215902 :     conn->wbuffers[current-1].offset = buffers[i].offset;
     364     3215902 :     conn->wbuffers[current-1].type = buff_unwritten;
     365             :
     366     3215902 :     previous = current;
     367     3215902 :     current = conn->wbuffers[current-1].next;
     368             :   }
     369             :
     370     1523253 :   if (!conn->wbuffer_first_towrite) {
     371     1026645 :     conn->wbuffer_first_towrite = conn->wbuffer_first_empty;
     372             :   }
     373     1523253 :   if (conn->wbuffer_last_towrite) {
     374      500389 :     conn->wbuffers[conn->wbuffer_last_towrite-1].next = conn->wbuffer_first_empty;
     375             :   }
     376             :
     377     1523253 :   conn->wbuffer_last_towrite = previous;
     378     1523253 :   conn->wbuffers[previous-1].next = 0;
     379     1523253 :   conn->wbuffer_first_empty = current;
     380             :
     381     1523253 :   conn->wbuffer_count += can_take;
     382     1523253 :   conn->wrequestedbuffers = false;
     383     1523253 :   return can_take;
     384             : }
~~~

## pni_raw_put_event_next

Slow case:

~~~ c
     662     5580985 : pn_event_t *pni_raw_event_next(pn_raw_connection_t *conn) {
     663     5580985 :   assert(conn);
     664     3099210 :   do {
     665     8680195 :     pn_event_t *event = pn_collector_next(conn->collector);
     666     8478476 :     if (event) {
     667     2965075 :       return pni_log_event(conn, event);
     668     5513401 :     } else if (conn->connectpending) {
     669           5 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_CONNECTED);
     670           5 :       conn->connectpending = false;
     671     5513396 :     } else if (conn->wakepending) {
     672     1244076 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_WAKE);
     673     1243671 :       conn->wakepending = false;
     674     4269320 :     } else if (conn->rpending) {
     675      621861 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_READ);
     676      619798 :       conn->rpending = false;
     677     3647459 :     } else if (conn->wpending) {
     678      622642 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_WRITTEN);
     679      621835 :       conn->wpending = false;
     680     3024817 :     } else if (conn->rclosedpending) {
     681           1 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_CLOSED_READ);
     682           1 :       conn->rclosedpending = false;
     683     3024816 :     } else if (conn->wclosedpending) {
     684           1 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_CLOSED_WRITE);
     685           1 :       conn->wclosedpending = false;
     686     3024815 :     } else if (conn->disconnectpending) {
     687           8 :       switch (conn->disconnect_state) {
     688           2 :       case disc_init:
     689           2 :         if (conn->rbuffer_first_read || conn->wbuffer_first_written) {
     690           1 :           pni_raw_put_event(conn, PN_RAW_CONNECTION_DRAIN_BUFFERS);
     691             :         }
     692           2 :         conn->disconnect_state = disc_drain_msg;
     693           2 :         break;
     694             :       // TODO: We'll leave the read/written events in here for the moment for backward compatibility
     695             :       // remove them soon (after dispatch uses DRAIN_BUFFER)
     696           2 :       case disc_drain_msg:
     697           2 :         if (conn->rbuffer_first_read) {
     698           1 :           pni_raw_put_event(conn, PN_RAW_CONNECTION_READ);
     699             :         }
     700           2 :         conn->disconnect_state = disc_read_msg;
     701           2 :         break;
     702           2 :       case disc_read_msg:
     703           2 :         if (conn->wbuffer_first_written) {
     704           0 :           pni_raw_put_event(conn, PN_RAW_CONNECTION_WRITTEN);
     705             :         }
     706           2 :         conn->disconnect_state = disc_written_msg;
     707           2 :         break;
     708           2 :       case disc_written_msg:
     709           2 :         pni_raw_put_event(conn, PN_RAW_CONNECTION_DISCONNECTED);
     710           2 :         conn->disconnectpending = false;
     711           2 :         conn->disconnect_state = disc_fini;
     712           2 :         break;
     713             :       }
     714     3024807 :     } else if (!pni_raw_wdrained(conn) && !conn->wbuffer_first_towrite && !conn->wrequestedbuffers) {
     715             :       // Ran out of write buffers
     716      614852 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_NEED_WRITE_BUFFERS);
     717      613886 :       conn->wrequestedbuffers = true;
     718     2432605 :     } else if (!pni_raw_rclosed(conn) && !conn->rbuffer_first_unused && !conn->rrequestedbuffers) {
     719             :       // Ran out of read buffers
     720           5 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_NEED_READ_BUFFERS);
     721           5 :       conn->rrequestedbuffers = true;
     722             :     } else {
     723     2451219 :       return NULL;
     724             :     }
     725             :   } while (true);
     726             : }
~~~

Slow case:

~~~ c
     662     3285462 : pn_event_t *pni_raw_event_next(pn_raw_connection_t *conn) {
     663     3285462 :   assert(conn);
     664     2113940 :   do {
     665     5399402 :     pn_event_t *event = pn_collector_next(conn->collector);
     666     5317063 :     if (event) {
     667     2060068 :       return pni_log_event(conn, event);
     668     3256995 :     } else if (conn->connectpending) {
     669           5 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_CONNECTED);
     670           5 :       conn->connectpending = false;
     671     3256990 :     } else if (conn->wakepending) {
     672      750161 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_WAKE);
     673      749515 :       conn->wakepending = false;
     674     2506829 :     } else if (conn->rpending) {
     675      191602 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_READ);
     676      191558 :       conn->rpending = false;
     677     2315227 :     } else if (conn->wpending) {
     678     1028711 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_WRITTEN);
     679     1028117 :       conn->wpending = false;
     680     1286516 :     } else if (conn->rclosedpending) {
     681           1 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_CLOSED_READ);
     682           1 :       conn->rclosedpending = false;
     683     1286515 :     } else if (conn->wclosedpending) {
     684           1 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_CLOSED_WRITE);
     685           1 :       conn->wclosedpending = false;
     686     1286514 :     } else if (conn->disconnectpending) {
     687           8 :       switch (conn->disconnect_state) {
     688           2 :       case disc_init:
     689           2 :         if (conn->rbuffer_first_read || conn->wbuffer_first_written) {
     690           1 :           pni_raw_put_event(conn, PN_RAW_CONNECTION_DRAIN_BUFFERS);
     691             :         }
     692           2 :         conn->disconnect_state = disc_drain_msg;
     693           2 :         break;
     694             :       // TODO: We'll leave the read/written events in here for the moment for backward compatibility
     695             :       // remove them soon (after dispatch uses DRAIN_BUFFER)
     696           2 :       case disc_drain_msg:
     697           2 :         if (conn->rbuffer_first_read) {
     698           1 :           pni_raw_put_event(conn, PN_RAW_CONNECTION_READ);
     699             :         }
     700           2 :         conn->disconnect_state = disc_read_msg;
     701           2 :         break;
     702           2 :       case disc_read_msg:
     703           2 :         if (conn->wbuffer_first_written) {
     704           0 :           pni_raw_put_event(conn, PN_RAW_CONNECTION_WRITTEN);
     705             :         }
     706           2 :         conn->disconnect_state = disc_written_msg;
     707           2 :         break;
     708           2 :       case disc_written_msg:
     709           2 :         pni_raw_put_event(conn, PN_RAW_CONNECTION_DISCONNECTED);
     710           2 :         conn->disconnectpending = false;
     711           2 :         conn->disconnect_state = disc_fini;
     712           2 :         break;
     713             :       }
     714     1286506 :     } else if (!pni_raw_wdrained(conn) && !conn->wbuffer_first_towrite && !conn->wrequestedbuffers) {
     715             :       // Ran out of write buffers
     716         927 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_NEED_WRITE_BUFFERS);
     717         927 :       conn->wrequestedbuffers = true;
     718     1307713 :     } else if (!pni_raw_rclosed(conn) && !conn->rbuffer_first_unused && !conn->rrequestedbuffers) {
     719             :       // Ran out of read buffers
     720      143818 :       pni_raw_put_event(conn, PN_RAW_CONNECTION_NEED_READ_BUFFERS);
     721      143808 :       conn->rrequestedbuffers = true;
     722             :     } else {
     723     1163574 :       return NULL;
     724             :     }
     725             :   } while (true);
     726             : }
~~~

## qd_raw_connection_grant_read_buffers

Slow case:

~~~ c
      74       44275 : int qd_raw_connection_grant_read_buffers(pn_raw_connection_t *pn_raw_conn)
      75             : {
      76       44275 :     assert(pn_raw_conn);
      77             :     pn_raw_buffer_t raw_buffers[RAW_BUFFER_BATCH];
      78       44275 :     size_t          desired = pn_raw_connection_read_buffers_capacity(pn_raw_conn);
      79       44275 :     const size_t    granted = desired;
      80             :
      81       88565 :     while (desired) {
      82             :         int i;
      83       88639 :         for (i = 0; i < desired && i < RAW_BUFFER_BATCH; ++i) {
      84       44349 :             qd_adaptor_buffer_t *buf = qd_adaptor_buffer();
      85       44350 :             raw_buffers[i].bytes    = (char *) qd_adaptor_buffer_base(buf);
      86       44350 :             raw_buffers[i].capacity = qd_adaptor_buffer_capacity(buf);
      87       44350 :             raw_buffers[i].size     = 0;
      88       44350 :             raw_buffers[i].offset   = 0;
      89       44350 :             raw_buffers[i].context  = (uintptr_t) buf;
      90             :         }
      91       44290 :         desired -= i;
      92       44290 :         pn_raw_connection_give_read_buffers(pn_raw_conn, raw_buffers, i);
      93             :     }
      94             :
      95       44276 :     return granted;
      96             : }
~~~

Fast case:

~~~ c
      74       48250 : int qd_raw_connection_grant_read_buffers(pn_raw_connection_t *pn_raw_conn)
      75             : {
      76       48250 :     assert(pn_raw_conn);
      77             :     pn_raw_buffer_t raw_buffers[RAW_BUFFER_BATCH];
      78       48250 :     size_t          desired = pn_raw_connection_read_buffers_capacity(pn_raw_conn);
      79       48250 :     const size_t    granted = desired;
      80             :
      81      170931 :     while (desired) {
      82             :         int i;
      83      611888 :         for (i = 0; i < desired && i < RAW_BUFFER_BATCH; ++i) {
      84      489281 :             qd_adaptor_buffer_t *buf = qd_adaptor_buffer();
      85      489201 :             raw_buffers[i].bytes    = (char *) qd_adaptor_buffer_base(buf);
      86      489201 :             raw_buffers[i].capacity = qd_adaptor_buffer_capacity(buf);
      87      489202 :             raw_buffers[i].size     = 0;
      88      489202 :             raw_buffers[i].offset   = 0;
      89      489202 :             raw_buffers[i].context  = (uintptr_t) buf;
      90             :         }
      91      122607 :         desired -= i;
      92      122607 :         pn_raw_connection_give_read_buffers(pn_raw_conn, raw_buffers, i);
      93             :     }
      94             :
      95       48245 :     return granted;
      96             : }
~~~

## qd_raw_connection_write_buffers

Slow case:

~~~ c
      98      179731 : int qd_raw_connection_write_buffers(pn_raw_connection_t *pn_raw_conn, qd_adaptor_buffer_list_t *blist)
      99      179731 : {
     100      179731 :     if (!pn_raw_conn)
     101           0 :         return 0;
     102             :
     103      179731 :     size_t pn_buffs_to_write     = pn_raw_connection_write_buffers_capacity(pn_raw_conn);
     104      179736 :     size_t qd_raw_buffs_to_write = DEQ_SIZE(*blist);
     105      179736 :     size_t num_buffs             = MIN(qd_raw_buffs_to_write, pn_buffs_to_write);
     106             :
     107      179736 :     if (num_buffs == 0)
     108      135472 :         return 0;
     109             :
     110       44264 :     pn_raw_buffer_t      raw_buffers[num_buffs];
     111       44264 :     qd_adaptor_buffer_t *qd_adaptor_buff = DEQ_HEAD(*blist);
     112             :
     113       44264 :     int i = 0;
     114             :
     115       88534 :     while (i < num_buffs) {
     116       44270 :         assert(qd_adaptor_buff != 0);
     117       44270 :         raw_buffers[i].bytes    = (char *) qd_adaptor_buffer_base(qd_adaptor_buff);
     118       44270 :         size_t buffer_size      = qd_adaptor_buffer_size(qd_adaptor_buff);
     119       44270 :         raw_buffers[i].size     = buffer_size;
     120       44270 :         raw_buffers[i].offset   = 0;
     121       44270 :         raw_buffers[i].capacity = 0;
     122       44270 :         raw_buffers[i].context = (uintptr_t) qd_adaptor_buff;
     123       44270 :         DEQ_REMOVE_HEAD(*blist);
     124       44270 :         qd_adaptor_buff = DEQ_HEAD(*blist);
     125       44270 :         i++;
     126             :     }
     127             :
     128       44264 :     size_t num_buffers_written = pn_raw_connection_write_buffers(pn_raw_conn, raw_buffers, num_buffs);
     129       44270 :     assert(num_buffs == num_buffers_written);
     130       44270 :     return num_buffers_written;
     131             : }
~~~

Fast case:

~~~ c
      98      349658 : int qd_raw_connection_write_buffers(pn_raw_connection_t *pn_raw_conn, qd_adaptor_buffer_list_t *blist)
      99      349658 : {
     100      349658 :     if (!pn_raw_conn)
     101           0 :         return 0;
     102             :
     103      349658 :     size_t pn_buffs_to_write     = pn_raw_connection_write_buffers_capacity(pn_raw_conn);
     104      349660 :     size_t qd_raw_buffs_to_write = DEQ_SIZE(*blist);
     105      349660 :     size_t num_buffs             = MIN(qd_raw_buffs_to_write, pn_buffs_to_write);
     106             :
     107      349660 :     if (num_buffs == 0)
     108       77869 :         return 0;
     109             :
     110      271791 :     pn_raw_buffer_t      raw_buffers[num_buffs];
     111      271791 :     qd_adaptor_buffer_t *qd_adaptor_buff = DEQ_HEAD(*blist);
     112             :
     113      271791 :     int i = 0;
     114             :
     115      791899 :     while (i < num_buffs) {
     116      520110 :         assert(qd_adaptor_buff != 0);
     117      520110 :         raw_buffers[i].bytes    = (char *) qd_adaptor_buffer_base(qd_adaptor_buff);
     118      520112 :         size_t buffer_size      = qd_adaptor_buffer_size(qd_adaptor_buff);
     119      520108 :         raw_buffers[i].size     = buffer_size;
     120      520108 :         raw_buffers[i].offset   = 0;
     121      520108 :         raw_buffers[i].capacity = 0;
     122      520108 :         raw_buffers[i].context = (uintptr_t) qd_adaptor_buff;
     123      520108 :         DEQ_REMOVE_HEAD(*blist);
     124      520108 :         qd_adaptor_buff = DEQ_HEAD(*blist);
     125      520108 :         i++;
     126             :     }
     127             :
     128      271789 :     size_t num_buffers_written = pn_raw_connection_write_buffers(pn_raw_conn, raw_buffers, num_buffs);
     129      271889 :     assert(num_buffs == num_buffers_written);
     130      271889 :     return num_buffers_written;
     131             : }
~~~

## qd_raw_connection_drain_write_buffers

Slow case:

~~~ c
     145           3 : int qd_raw_connection_drain_write_buffers(pn_raw_connection_t *pn_raw_conn)
     146             : {
     147             :     pn_raw_buffer_t buffs[RAW_BUFFER_BATCH];
     148             :     size_t          n;
     149           3 :     int             write_buffers_drained = 0;
     150           3 :     while ((n = pn_raw_connection_take_written_buffers(pn_raw_conn, buffs, RAW_BUFFER_BATCH))) {
     151           0 :         for (size_t i = 0; i < n; ++i) {
     152           0 :             write_buffers_drained++;
     153           0 :             qd_adaptor_buffer_t *qd_adaptor_buffer = (qd_adaptor_buffer_t *) buffs[i].context;
     154           0 :             qd_adaptor_buffer_free(qd_adaptor_buffer);
     155             :         }
     156             :     }
     157           3 :     return write_buffers_drained;
     158             : }
~~~

Fast case:

~~~ c
     145           9 : int qd_raw_connection_drain_write_buffers(pn_raw_connection_t *pn_raw_conn)
     146             : {
     147             :     pn_raw_buffer_t buffs[RAW_BUFFER_BATCH];
     148             :     size_t          n;
     149           9 :     int             write_buffers_drained = 0;
     150          14 :     while ((n = pn_raw_connection_take_written_buffers(pn_raw_conn, buffs, RAW_BUFFER_BATCH))) {
     151          18 :         for (size_t i = 0; i < n; ++i) {
     152          13 :             write_buffers_drained++;
     153          13 :             qd_adaptor_buffer_t *qd_adaptor_buffer = (qd_adaptor_buffer_t *) buffs[i].context;
     154          13 :             qd_adaptor_buffer_free(qd_adaptor_buffer);
     155             :         }
     156             :     }
     157           9 :     return write_buffers_drained;
     158             : }
~~~

## grant_read_buffers in tcp_adaptor.c

Slow case:

~~~ c
     221       44276 : static void grant_read_buffers(qdr_tcp_connection_t *conn, const char *msg)
     222             : {
     223       44276 :     if (IS_ATOMIC_FLAG_SET(&conn->raw_closed_read) || read_window_full(conn))
     224           1 :         return;
     225       44275 :     int granted_read_buffers = qd_raw_connection_grant_read_buffers(conn->pn_raw_conn);
     226       44276 :     qd_log(tcp_adaptor->log_source, QD_LOG_DEBUG,
     227             :            "[C%" PRIu64 "] grant_read_buffers(%s) granted %i read buffers to proton raw api", conn->conn_id, msg,
     228             :            granted_read_buffers);
     229             : }
~~~

Fast case:

~~~ c
     221       76673 : static void grant_read_buffers(qdr_tcp_connection_t *conn, const char *msg)
     222             : {
     223       76673 :     if (IS_ATOMIC_FLAG_SET(&conn->raw_closed_read) || read_window_full(conn))
     224       28425 :         return;
     225       48248 :     int granted_read_buffers = qd_raw_connection_grant_read_buffers(conn->pn_raw_conn);
     226       48245 :     qd_log(tcp_adaptor->log_source, QD_LOG_DEBUG,
     227             :            "[C%" PRIu64 "] grant_read_buffers(%s) granted %i read buffers to proton raw api", conn->conn_id, msg,
     228             :            granted_read_buffers);
     229             : }
~~~

## qdr_tcp_q2_unblocked_handler

Slow case:

~~~ c
     257           0 : void qdr_tcp_q2_unblocked_handler(const qd_alloc_safe_ptr_t context)
     258             : {
     259           0 :     qdr_tcp_connection_t *tc = (qdr_tcp_connection_t*)qd_alloc_deref_safe_ptr(&context);
     260           0 :     if (tc == 0) {
     261             :         // bad news.
     262           0 :         assert(false);
     263             :         return;
     264             :     }
     265             :
     266             :     // prevent the tc from being deleted while running:
     267           0 :     LOCK(&tc->activation_lock);
     268             :
     269           0 :     if (tc->pn_raw_conn) {
     270           0 :         sys_atomic_set(&tc->q2_restart, 1);
     271           0 :         qd_log(tcp_adaptor->log_source, QD_LOG_DEBUG,
     272             :                "[C%"PRIu64"] q2 unblocked: call pn_raw_connection_wake()",
     273             :                tc->conn_id);
     274           0 :         pn_raw_connection_wake(tc->pn_raw_conn);
     275             :     }
     276             :
     277           0 :     UNLOCK(&tc->activation_lock);
     278             : }
~~~

Fast case:

~~~ c
     257       30575 : void qdr_tcp_q2_unblocked_handler(const qd_alloc_safe_ptr_t context)
     258             : {
     259       30575 :     qdr_tcp_connection_t *tc = (qdr_tcp_connection_t*)qd_alloc_deref_safe_ptr(&context);
     260       30575 :     if (tc == 0) {
     261             :         // bad news.
     262           0 :         assert(false);
     263             :         return;
     264             :     }
     265             :
     266             :     // prevent the tc from being deleted while running:
     267       30575 :     LOCK(&tc->activation_lock);
     268             :
     269       30575 :     if (tc->pn_raw_conn) {
     270       30575 :         sys_atomic_set(&tc->q2_restart, 1);
     271       30575 :         qd_log(tcp_adaptor->log_source, QD_LOG_DEBUG,
     272             :                "[C%"PRIu64"] q2 unblocked: call pn_raw_connection_wake()",
     273             :                tc->conn_id);
     274       30575 :         pn_raw_connection_wake(tc->pn_raw_conn);
     275             :     }
     276             :
     277       30575 :     UNLOCK(&tc->activation_lock);
     278             : }
~~~

## read_message_body in tcp_adaptor.c

Slow case:

~~~ c
     657      223975 : static int read_message_body(qdr_tcp_connection_t *conn, qd_message_t *msg, pn_raw_buffer_t *buffers, int count)
     658             : {
     659      223975 :     int used = 0;
     660             :
     661             :     // Advance to next stream_data vbin segment if necessary.
     662             :     // Return early if no data to process or error
     663      223975 :     if (conn->outgoing_stream_data == 0) {
     664      223976 :         qd_message_stream_data_result_t stream_data_result = qd_message_next_stream_data(msg, &conn->outgoing_stream_data);
     665      224029 :         if (stream_data_result == QD_MESSAGE_STREAM_DATA_BODY_OK) {
     666             :             // a new stream_data segment has been found
     667       44270 :             conn->outgoing_body_bytes  = 0;
     668       44270 :             conn->outgoing_body_offset = 0;
     669             :             // continue to process this segment
     670      179759 :         } else if (stream_data_result == QD_MESSAGE_STREAM_DATA_INCOMPLETE) {
     671      179754 :             return 0;
     672             :         } else {
     673           5 :             switch (stream_data_result) {
     674           0 :             case QD_MESSAGE_STREAM_DATA_NO_MORE:
     675           0 :                 qd_log(tcp_adaptor->log_source, QD_LOG_INFO,
     676             :                        "[C%"PRIu64"] EOS", conn->conn_id);
     677           0 :                 conn->read_eos_seen = true;
     678           0 :                 break;
     679           0 :             case QD_MESSAGE_STREAM_DATA_INVALID:
     680           0 :                 qd_log(tcp_adaptor->log_source, QD_LOG_ERROR,
     681             :                        "[C%"PRIu64"] Invalid body data for streaming message", conn->conn_id);
     682           0 :                 break;
     683           5 :             default:
     684           5 :                 break;
     685             :             }
     686           5 :             qd_message_set_send_complete(msg);
     687           0 :             return -1;
     688             :         }
     689             :     }
     690             :
     691             :     // A valid stream_data is in place.
     692             :     // Try to get a buffer set from it.
     693       44269 :     used = qd_message_stream_data_buffers(conn->outgoing_stream_data, buffers, conn->outgoing_body_offset, count);
     694       44270 :     if (used > 0) {
     695             :         // Accumulate the lengths of the returned buffers.
     696     1505180 :         for (int i=0; i<used; i++) {
     697     1460910 :             conn->outgoing_body_bytes += buffers[i].size;
     698             :         }
     699             :
     700             :         // Buffers returned should never exceed the stream_data payload length
     701       44270 :         assert(conn->outgoing_body_bytes <= conn->outgoing_stream_data->payload.length);
     702             :
     703       44270 :         if (conn->outgoing_body_bytes == conn->outgoing_stream_data->payload.length) {
     704             :             // Erase the stream_data struct from the connection so that
     705             :             // a new one gets created on the next pass.
     706       44270 :             conn->previous_stream_data = conn->outgoing_stream_data;
     707       44270 :             conn->outgoing_stream_data = 0;
     708             :         } else {
     709             :             // Returned buffer set did not consume the entire stream_data segment.
     710             :             // Leave existing stream_data struct in place for use on next pass.
     711             :             // Add the number of returned buffers to the offset for the next pass.
     712           0 :             conn->outgoing_body_offset += used;
     713             :         }
     714             :     } else {
     715             :         // No buffers returned.
     716             :         // This sender has caught up with all data available on the input stream.
     717             :     }
     718       44270 :     return used;
     719             : }
~~~

Fast case:

~~~ c
     657      377367 : static int read_message_body(qdr_tcp_connection_t *conn, qd_message_t *msg, pn_raw_buffer_t *buffers, int count)
     658             : {
     659      377367 :     int used = 0;
     660             :
     661             :     // Advance to next stream_data vbin segment if necessary.
     662             :     // Return early if no data to process or error
     663      377367 :     if (conn->outgoing_stream_data == 0) {
     664      255042 :         qd_message_stream_data_result_t stream_data_result = qd_message_next_stream_data(msg, &conn->outgoing_stream_data);
     665      255092 :         if (stream_data_result == QD_MESSAGE_STREAM_DATA_BODY_OK) {
     666             :             // a new stream_data segment has been found
     667      153109 :             conn->outgoing_body_bytes  = 0;
     668      153109 :             conn->outgoing_body_offset = 0;
     669             :             // continue to process this segment
     670      101983 :         } else if (stream_data_result == QD_MESSAGE_STREAM_DATA_INCOMPLETE) {
     671      101999 :             return 0;
     672             :         } else {
     673           0 :             switch (stream_data_result) {
     674           0 :             case QD_MESSAGE_STREAM_DATA_NO_MORE:
     675           0 :                 qd_log(tcp_adaptor->log_source, QD_LOG_INFO,
     676             :                        "[C%"PRIu64"] EOS", conn->conn_id);
     677           0 :                 conn->read_eos_seen = true;
     678           0 :                 break;
     679           0 :             case QD_MESSAGE_STREAM_DATA_INVALID:
     680           0 :                 qd_log(tcp_adaptor->log_source, QD_LOG_ERROR,
     681             :                        "[C%"PRIu64"] Invalid body data for streaming message", conn->conn_id);
     682           0 :                 break;
     683           0 :             default:
     684           0 :                 break;
     685             :             }
     686           0 :             qd_message_set_send_complete(msg);
     687           0 :             return -1;
     688             :         }
     689             :     }
     690             :
     691             :     // A valid stream_data is in place.
     692             :     // Try to get a buffer set from it.
     693      275434 :     used = qd_message_stream_data_buffers(conn->outgoing_stream_data, buffers, conn->outgoing_body_offset, count);
     694      275536 :     if (used > 0) {
     695             :         // Accumulate the lengths of the returned buffers.
     696    16093797 :         for (int i=0; i<used; i++) {
     697    15818261 :             conn->outgoing_body_bytes += buffers[i].size;
     698             :         }
     699             :
     700             :         // Buffers returned should never exceed the stream_data payload length
     701      275536 :         assert(conn->outgoing_body_bytes <= conn->outgoing_stream_data->payload.length);
     702             :
     703      275536 :         if (conn->outgoing_body_bytes == conn->outgoing_stream_data->payload.length) {
     704             :             // Erase the stream_data struct from the connection so that
     705             :             // a new one gets created on the next pass.
     706      153098 :             conn->previous_stream_data = conn->outgoing_stream_data;
     707      153098 :             conn->outgoing_stream_data = 0;
     708             :         } else {
     709             :             // Returned buffer set did not consume the entire stream_data segment.
     710             :             // Leave existing stream_data struct in place for use on next pass.
     711             :             // Add the number of returned buffers to the offset for the next pass.
     712      122438 :             conn->outgoing_body_offset += used;
     713             :         }
     714             :     } else {
     715             :         // No buffers returned.
     716             :         // This sender has caught up with all data available on the input stream.
     717             :     }
     718      275536 :     return used;
     719             : }
~~~
