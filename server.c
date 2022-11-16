#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 45674

typedef struct thread_data {
    int client_socket;
    int buffer_size;
} thread_data;

void* run(void* data) {
    int client_socket = ((thread_data*) data)->client_socket;
    int buffer_size = ((thread_data*) data)->buffer_size;
    char* buffer = (char*) malloc(buffer_size);

    while (1) {
        ssize_t received = recv(client_socket, buffer, buffer_size, 0);

        if (received == 0) goto cleanup;
        if (received < 0) goto error;

        ssize_t sent = send(client_socket, buffer, received, 0);

        if (sent < 0) goto error;
    }

error:
    fprintf(stderr, "ERROR! %s\n", strerror(errno));

cleanup:
    close(client_socket);
    free(buffer);

    pthread_exit(NULL);
}

int main(size_t argc, char** argv) {
    int server_socket = -1;
    int err;

    struct sockaddr_in addr = (struct sockaddr_in) {
        0,
        .sin_family = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
        .sin_port = htons(PORT)
    };

    server_socket = socket(AF_INET, SOCK_STREAM, 0);

    if (server_socket < 0) goto error;

    int opt = 1;
    err = setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    if (err) goto error;

    err = bind(server_socket, (const struct sockaddr*) &addr, sizeof(addr));

    if (err) goto error;

    printf("Bound!\n");

    err = listen(server_socket, 1);

    if (err) goto error;

    printf("Listening!\n");

    while (1) {
        int client_socket = accept(server_socket, NULL, NULL);

        if (client_socket < 0) goto error;

        pthread_t* thread = malloc(sizeof(pthread_t));
        thread_data* data = malloc(sizeof(thread_data));

        *data = (thread_data) {
            .client_socket = client_socket,
            .buffer_size = 16384
        };

        pthread_create(thread, NULL, &run, (void*) data);
    }

error:
    fprintf(stderr, "ERROR! %s\n", strerror(errno));

    if (server_socket > 0) shutdown(server_socket, SHUT_RDWR);

    exit(-1);
}
