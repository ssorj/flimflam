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
