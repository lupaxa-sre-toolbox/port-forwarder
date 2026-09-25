# Reference

## CLI Arguments

| Argument | Required | Description                                                   |
| :------- | :------- | :------------------------------------------------------------ |
| `TARGET` | yes      | `LOCAL HOST REMOTE`, or one or more `LOCAL:HOST:REMOTE` items |

| Flag                | Default     | Description                                  |
| :------------------ | :---------- | :------------------------------------------- |
| `--bind`            | `127.0.0.1` | Local address to bind                        |
| `--timeout`         | `10`        | Remote connect timeout in seconds            |
| `--max-connections` | unlimited   | Max concurrent sessions per listener         |
| `--allow`           | off         | Repeatable source IP or CIDR allowlist       |
| `--idle-timeout`    | off         | Close a session after this many idle seconds |
| `--verbose`         | off         | Log debug detail                             |
| `--quiet`           | off         | Log warnings and errors only                 |
| `--version`         | —           | Print the package version and exit           |

`--timeout` and `--idle-timeout` must be greater than `0` when set.
`--max-connections` must be at least `1` when set. `--verbose` and
`--quiet` are mutually exclusive. IPv6 remotes use
`LOCAL:[IPv6]:REMOTE`.

## Exit Codes

| Code | When                                                        |
| :--- | :---------------------------------------------------------- |
| `0`  | Help, version, or a clean stop with `Ctrl+C` or `SIGTERM`   |
| `1`  | Invalid arguments, or a listener failed to bind             |

## Library

| Name                      | Meaning                                                       |
| :------------------------ | :------------------------------------------------------------ |
| `PortForwarder`           | Listener that relays each client to `remote_host:remote_port` |
| `PortForwarderGroup`      | Start and stop several forwarders together                    |
| `Mapping`                 | One `local_port`, `remote_host`, and `remote_port`            |
| `bound_port`              | Actual listen port after `start()` binds                      |
| `start()`                 | Bind, listen, and accept until `stop()`                       |
| `stop()`                  | Close the listener and in-flight sockets                      |
| `prune_sessions()`        | Drop finished session threads from the tracked list           |
| `session_threads`         | Snapshot of session threads, including finished ones          |
| `connect_timeout`         | Seconds to wait when opening the remote side                  |
| `max_connections`         | Per-listener session cap, or `None` for unlimited             |
| `idle_timeout`            | Idle close in seconds, or `None` to leave sessions open       |
| `DEFAULT_CONNECT_TIMEOUT` | Default remote connect timeout (`10`)                         |
| `DEFAULT_BACKLOG`         | Default listen backlog (`128`)                                |
| `parse_targets()`         | Parse legacy triples or `LOCAL:HOST:REMOTE` mappings          |
| `parse_allow()`           | Parse host addresses or CIDR networks                         |
| `get_version()`           | Return the package version string                             |

`PortForwarder.bound_port` raises `RuntimeError` if `start()` has not
bound a socket yet. The class is a context manager: leaving `with`
calls `stop()`.

Remote connections use `socket.create_connection`, so IPv4 and IPv6
targets both work. The listen socket uses IPv6 when `--bind` /
`bind_host` contains a colon. IPv4-mapped IPv6 sources are compared as
IPv4 against `--allow`.
