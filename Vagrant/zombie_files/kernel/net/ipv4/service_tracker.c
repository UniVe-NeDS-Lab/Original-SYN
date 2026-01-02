// SPDX-License-Identifier: GPL-2.0
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/random.h>
#include <linux/jiffies.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/hashtable.h>
#include <net/inet_sock.h>
#include <net/sock.h>
#include <net/service_tracker.h>

#define TOKEN_LIFETIME (10 * 60 * HZ)   // 10 minutes in jiffies
#define SERVICE_HASH_BITS 6            // Hashtable size: 2^6 = 64 buckets

/* Structure to store per-service token and service_backlog_value */
struct service_token_entry {
	struct hlist_node hnode;         // Hashtable node linkage
	u16 port;                        // TCP port number
	u32 token;                       // Random token (regenerated every 10 min)
	u32 service_backlog_value;       // Custom user-defined field (default: -1)
	unsigned long last_update;       // Time of last token update (in jiffies)
};

/* Global hashtable and lock */
static DEFINE_HASHTABLE(service_token_table, SERVICE_HASH_BITS);
static DEFINE_SPINLOCK(service_token_lock);

/**
 * find_or_create_service_entry - Retrieve or create a token entry for a given TCP port.
 * @port: TCP port (in host byte order)
 * Return: pointer to the service_token_entry, or NULL on failure
 */
static struct service_token_entry *find_or_create_service_entry(u16 port)
{
	struct service_token_entry *entry;
	unsigned long now = jiffies;
	u32 hash_key = port;
	bool found = false;

	spin_lock(&service_token_lock);

	hash_for_each_possible(service_token_table, entry, hnode, hash_key) {
		if (entry->port == hash_key) {
			found = true;

			// Refresh token if expired
			if (time_after(now, entry->last_update + TOKEN_LIFETIME)) {
				get_random_bytes(&entry->token, sizeof(u32));
				entry->last_update = now;
				entry->service_backlog_value = U32_MAX;
				pr_info("service_token: Token updated for port %u: 0x%x\n",
				        port, entry->token);
			}
			break;
		}
	}

	if (!found) {
		entry = kzalloc(sizeof(*entry), GFP_ATOMIC);
		if (!entry) {
			spin_unlock(&service_token_lock);
			pr_warn("service_token: Allocation failed for port %u\n", port);
			return NULL;
		}

		entry->port = port;
		entry->service_backlog_value = U32_MAX;  // Default service_backlog_value
		get_random_bytes(&entry->token, sizeof(u32));
		entry->last_update = now;

		hash_add(service_token_table, &entry->hnode, hash_key);

		pr_info("service_token: New token created for port %u: 0x%x\n",
		        port, entry->token);
	}

	spin_unlock(&service_token_lock);
	return entry;
}

/**
 * get_service_token - Get the current token for the listener socket's port.
 * @sk_listener: Pointer to the listener socket
 * Return: 32-bit token value (or 0 on failure)
 */
u32 get_service_token(struct sock *sk_listener)
{
	u16 port = ntohs(inet_sk(sk_listener)->inet_num);
	struct service_token_entry *entry = find_or_create_service_entry(port);

	return entry ? entry->token : 0;
}

/**
 * get_service_service_backlog_value - Get the 'service_backlog_value' value for a specific listener socket.
 * @sk_listener: Pointer to the li
stener socket
 * Return: Range value, or -1 if not found
 */
u32 get_service_backlog_value(struct sock *sk_listener)
{
	u16 port = ntohs(inet_sk(sk_listener)->inet_num);
	struct service_token_entry *entry;
	int value = U32_MAX;

	spin_lock(&service_token_lock);

	hash_for_each_possible(service_token_table, entry, hnode, port) {
		if (entry->port == port) {
			value = entry->service_backlog_value;
			break;
		}
	}

	spin_unlock(&service_token_lock);
	return value;
}

/**
 * set_service_service_backlog_value - Set the 'service_backlog_value' value for a specific listener socket.
 * @sk_listener: Pointer to the listener socket
 * @new_service_backlog_value: New integer value to store
 * Return: 0 on success, -1 if the service is not found
 */

int set_service_backlog_value(struct sock *sk_listener, int new_service_backlog_value)
{
	u16 port = ntohs(inet_sk(sk_listener)->inet_num);
	struct service_token_entry *entry;
	int ret = -1;

	spin_lock(&service_token_lock);

	hash_for_each_possible(service_token_table, entry, hnode, port) {
		if (entry->port == port) {
			entry->service_backlog_value = (u32)new_service_backlog_value;
			pr_info("service_token: Range updated for port %u: %d\n", port, new_service_backlog_value);
			ret = 0;
			break;
		}
	}

	spin_unlock(&service_token_lock);
	return ret;
}

/**
 * cleanup_service_tokens - Frees all entries from the service token hashtable.
 * Call this during module unload or cleanup phase.
 */
void cleanup_service_tokens(void)
{
	struct service_token_entry *entry;
	struct hlist_node *tmp;
	int bkt;

	spin_lock(&service_token_lock);

	hash_for_each_safe(service_token_table, bkt, tmp, entry, hnode) {
		hash_del(&entry->hnode);
		kfree(entry);
	}

	spin_unlock(&service_token_lock);

	pr_info("service_token: All token entries cleaned up.\n");
}


/**
 * cleanup_service_token_by_port - Removes a single token entry by TCP port.
 * @port: TCP port (host byte order)
 * Return: 0 on success, -1 if not found
 */
int cleanup_service_token_by_port(u16 port)
{
	struct service_token_entry *entry;
	u32 hash_key = port;
	int ret = -1;

	spin_lock(&service_token_lock);

	hash_for_each_possible(service_token_table, entry, hnode, hash_key) {
		if (entry->port == port) {
			hash_del(&entry->hnode);
			kfree(entry);
			pr_info("service_token: Entry removed for port %u\n", port);
			ret = 0;
			break;
		}
	}

	spin_unlock(&service_token_lock);
	return ret;
}
