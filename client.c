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
    int socket;
    int port;
    int buffer_size;
} thread_context_t;

void* run(void* data) {
    int id = ((thread_context_t*) data)->id;
    int sock = ((thread_context_t*) data)->socket;
    int port = ((thread_context_t*) data)->port;
    int buffer_size = ((thread_context_t*) data)->buffer_size;
    size_t total_received = 0;

    char* buffer = (char*) malloc(buffer_size);
    memset(buffer, 'x', buffer_size);

    char transfers_file[256];
    snprintf(transfers_file, 256, "transfers.%d.csv", id);

    FILE* transfers = fopen(transfers_file, "w");
    if (!transfers) goto egress;

    struct sockaddr_in addr = (struct sockaddr_in) {
        0,
        .sin_family = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
        .sin_port = htons(port)
    };

    int err = connect(sock, (const struct sockaddr*) &addr, sizeof(addr));
    if (err) goto egress;

    printf("Connected!\n");

    while (1) {
        ssize_t sent = send(sock, buffer, buffer_size, 0);
        if (sent < 0) break;

        ssize_t received = recv(sock, buffer, buffer_size, 0);
        if (received < 0) break;

        if (received == 0) {
            break;
        }

        total_received += received;

        fprintf(transfers, "%d,%d,%lu\n", sent, received, total_received);
        fflush(transfers);
    }

egress:
    if (errno) {
        fprintf(stderr, "ERROR! %s\n", strerror(errno));
    }

    fclose(transfers);
    free(buffer);

    return NULL;
}

int main(size_t argc, char** argv) {
    int port = atoi(argv[1]);
    int buffer_size = atoi(argv[2]);
    int jobs = atoi(argv[3]);

    pthread_t threads[jobs];
    thread_context_t contexts[jobs];

    for (int i = 0; i < jobs; i++) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) goto egress;

        contexts[i] = (thread_context_t) {
            .id = i,
            .socket = sock,
            .port = port,
            .buffer_size = buffer_size
        };

        pthread_create(&threads[i], NULL, &run, (void*) &contexts[i]);
    }

    for (int i = 0; i < jobs; i++) {
        pthread_join(threads[i], NULL);
    }

egress:
    if (errno) {
        fprintf(stderr, "ERROR! %s\n", strerror(errno));
    }

    for (int i = 0; i < jobs; i++) {
        if (contexts[i].socket) close(contexts[i].socket);
    }

    exit(errno);
}
