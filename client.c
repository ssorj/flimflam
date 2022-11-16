#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PORT 45673
// #define BUFFER_SIZE 16384
#define BUFFER_SIZE 16385

void* run(void* data) {
    int sock = -1;
    int thread_id = *((int *) data);
    char* transfers_file = (char*) malloc(256);
    char* buffer = (char*) malloc(BUFFER_SIZE);

    snprintf(transfers_file, 256, "transfers.%d.csv", thread_id);

    FILE* transfers = fopen(transfers_file, "w");

    if (!transfers) goto error;

    memset(buffer, 'x', BUFFER_SIZE);

    struct sockaddr_in addr = (struct sockaddr_in) {
        0,
        .sin_family = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
        .sin_port = htons(PORT)
    };

    sock = socket(AF_INET, SOCK_STREAM, 0);

    if (sock < 0) goto error;

    int err = connect(sock, (const struct sockaddr*) &addr, sizeof(addr));

    if (err) goto error;

    printf("Connected!\n");

    size_t total = 0;

    while (1) {
        ssize_t sent = send(sock, buffer, BUFFER_SIZE, 0);

        if (sent < 0) goto error;

        ssize_t received = recv(sock, buffer, BUFFER_SIZE, 0);

        if (received == 0) {
            fclose(transfers);
            return NULL;
        }

        if (received < 0) goto error;

        total += received;

        fprintf(transfers, "%d,%d,%lu\n", sent, received, total);
        fflush(transfers);
    }

error:
    fprintf(stderr, "ERROR! %s\n", strerror(errno));

    if (sock < 0) close(sock);

    pthread_exit(NULL);
}

int main(size_t argc, char** argv) {
    int jobs = atoi(argv[1]);

    int thread_ids[jobs];
    pthread_t threads[jobs];

    for (int i = 0; i < jobs; i++) {
        thread_ids[i] = i;
        pthread_create(&threads[i], NULL, &run, (void*) &thread_ids[i]);
    }

    for (int i = 0; i < jobs; i++) {
        pthread_join(threads[i], NULL);
    }

    return 0;
}
