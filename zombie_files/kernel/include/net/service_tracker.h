#ifndef _TCP_SERVICE_TOKEN_H
#define _TCP_SERVICE_TOKEN_H

#include <net/sock.h>


u32 get_service_token(struct sock *sk_listener);
int set_service_backlog_value(struct sock *sk_listener, int new_service_backlog_value);
u32 get_service_backlog_value(struct sock *sk_listener);
void cleanup_service_tokens(void);
int cleanup_service_token_by_port(u16 port);

#endif
