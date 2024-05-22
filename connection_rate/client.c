/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>



typedef struct thread_context {
    int id;
    int port;
    char* output_dir;
} thread_context_t;


void *
//client ( char * output_dir, int id, int port ) {
client(void * data) {
    thread_context_t * ctx = (thread_context_t *) data;
    char * output_dir = ctx->output_dir;
    int id            = ctx->id;
    int port          = ctx->port;

    // Get the output file
    char transfers_file[256];
    snprintf(transfers_file, 256, "%s/transfers.%d.csv", output_dir, id);

    FILE* transfers = fopen(transfers_file, "w");
    if (!transfers) goto egress;

    int connection_count = 0;

    while ( 1 ) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);  // socket
        if (sock < 0) goto egress;

        struct sockaddr_in addr = (struct sockaddr_in) {
            0,
            .sin_family = AF_INET,
            .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
            .sin_port = htons(port)
        };

        int err = connect(sock, (const struct sockaddr*) &addr, sizeof(addr));
        if (err) goto egress;

        char str[100];
        int n = read(sock, str, 100);
        if (n < 0) goto egress;
        close(sock);

        ++ connection_count;
        fprintf(transfers, "%d,%d\n", 2, connection_count);
        fflush(transfers);
    }

egress:

    fclose(transfers);

    if (errno) {
        fprintf(stderr, "client: ERROR! %s\n", strerror(errno));
    }
}


int main(size_t argc, char** argv) {
    
    if (argc != 4) {
        fprintf(stderr, "Usage: client PORT JOBS OUTPUT-DIR\n");
        return 1;
    }


    int port = atoi(argv[1]);
    int jobs = atoi(argv[2]);
    char* output_dir = argv[3];

    thread_context_t contexts       [jobs];
    pthread_t        client_threads [jobs];

    for (int i = 0; i < jobs; i++) {
      contexts[i] = (thread_context_t) {
          .id = i,
          .port = port,
          .output_dir = output_dir,
      };
      pthread_create(client_threads+i, NULL, &client, contexts+i);
    }

    for (int i = 0; i < jobs; i++) {
      pthread_join(client_threads[i], NULL);
    }

    exit(errno);
}
