#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 45674
#define BUFFER_SIZE 16384

void* run(void* data) {
    int client_sock = *((int *) data);
    char* buffer = (char*) malloc(BUFFER_SIZE);

    while (1) {
        ssize_t received = recv(client_sock, buffer, BUFFER_SIZE, 0);

        if (received == 0) {
            pthread_exit(NULL);
        }

        if (received < 0) goto error;

        ssize_t sent = send(client_sock, buffer, received, 0);

        if (sent < 0) goto error;
    }

error:
    fprintf(stderr, "ERROR! %s\n", strerror(errno));

    close(client_sock);

    pthread_exit(NULL);
}

int main(size_t argc, char** argv) {
    int server_sock = -1;
    int err;

    struct sockaddr_in addr = (struct sockaddr_in) {
        0,
        .sin_family = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
        .sin_port = htons(PORT)
    };

    server_sock = socket(AF_INET, SOCK_STREAM, 0);

    if (server_sock < 0) goto error;

    int opt = 1;
    err = setsockopt(server_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    if (err) goto error;

    err = bind(server_sock, (const struct sockaddr*) &addr, sizeof(addr));

    if (err) goto error;

    printf("Bound!\n");

    err = listen(server_sock, 1);

    if (err) goto error;

    printf("Listening!\n");

    while (1) {
        int client_sock = accept(server_sock, NULL, NULL);

        if (client_sock < 0) goto error;

        pthread_t* thread = malloc(sizeof(pthread_t));
        int* thread_data = malloc(sizeof(int));

        *thread_data = client_sock;

        pthread_create(thread, NULL, &run, (void*) thread_data);
    }

error:
    fprintf(stderr, "ERROR! %s\n", strerror(errno));

    if (server_sock< 0) close(server_sock);

    exit(-1);
}
