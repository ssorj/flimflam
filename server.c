#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

typedef struct thread_context {
    int socket;
    int buffer_size;
} thread_context_t;

void* run(void* data) {
    int sock = ((thread_context_t*) data)->socket;
    int buffer_size = ((thread_context_t*) data)->buffer_size;
    char* buffer = (char*) malloc(buffer_size);

    while (1) {
        ssize_t received = recv(sock, buffer, buffer_size, 0);
        if (received == 0 || received < 0) break;

        ssize_t sent = send(sock, buffer, received, 0);
        if (sent < 0) break;
    }

    if (errno) {
        fprintf(stderr, "ERROR! %s\n", strerror(errno));
    }

    close(sock);
    free(buffer);

    return NULL;
}

int main(size_t argc, char** argv) {
    int port = atoi(argv[1]);
    int buffer_size = atoi(argv[2]);

    int server_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (server_sock < 0) goto egress;

    int opt = 1;
    int err = setsockopt(server_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    if (err) goto egress;

    struct sockaddr_in addr = (struct sockaddr_in) {
        0,
        .sin_family = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
        .sin_port = htons(port)
    };

    err = bind(server_sock, (const struct sockaddr*) &addr, sizeof(addr));
    if (err) goto egress;

    err = listen(server_sock, 1);
    if (err) goto egress;

    printf("Listening!\n");

    while (1) {
        int sock = accept(server_sock, NULL, NULL);
        if (sock < 0) goto egress;

        printf("Accepted!\n");

        pthread_t* thread = malloc(sizeof(pthread_t));
        thread_context_t* context = malloc(sizeof(thread_context_t));

        *context = (thread_context_t) {
            .socket = sock,
            .buffer_size = buffer_size
        };

        pthread_create(thread, NULL, &run, (void*) context);
    }

egress:
    if (errno) {
        fprintf(stderr, "ERROR! %s\n", strerror(errno));
    }

    if (server_sock > 0) shutdown(server_sock, SHUT_RDWR);

    exit(errno);
}
