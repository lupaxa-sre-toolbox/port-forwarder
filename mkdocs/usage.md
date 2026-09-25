# Usage

Pass a single `LOCAL HOST REMOTE` triple, or one or more
`LOCAL:HOST:REMOTE` mappings. Each accepted client opens a new
connection to that mapping's remote endpoint and relays bytes both
ways. Shared flags apply to every mapping.

IPv6 remotes use brackets: `8080:[::1]:80`.

## CLI Flags

| Flag                | Default     | Description                                    |
| :------------------ | :---------- | :--------------------------------------------- |
| `--bind`            | `127.0.0.1` | Local address to listen on                     |
| `--timeout`         | `10`        | Remote connect timeout in seconds              |
| `--max-connections` | unlimited   | Max concurrent sessions per listener           |
| `--allow`           | off         | Repeatable source IP or CIDR allowlist         |
| `--idle-timeout`    | off         | Close a session after this many idle seconds   |
| `--verbose`         | off         | Log debug detail                               |
| `--quiet`           | off         | Log warnings and errors only                   |
| `--version`         | —           | Print the package version and exit             |

`--verbose` and `--quiet` cannot be combined. `--allow` is most useful
with `--bind 0.0.0.0`. `--timeout` is the remote connect bound; it is
not the idle timer.

```bash
port-forwarder 8080 remote.example.com 80
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
port-forwarder 5432 db.internal 5432 --bind 0.0.0.0 --allow 10.0.0.0/8
port-forwarder 8080 remote.example.com 80 --max-connections 8 --idle-timeout 60
port-forwarder 8080 remote.example.com 80 --timeout 2.5
port-forwarder --version
```

Listen ports and remote ports must be integers from `1` to `65535`.

The process runs until it is interrupted. `Ctrl+C` or `SIGTERM` closes
the listen sockets, waits for in-flight relays, and exits `0`. A bind
or listen failure prints an error to stderr and exits `1`.

When one side half-closes its write stream, the other direction stays
open so the reply can still arrive.

## Library

```python
from lupaxa.port_forwarder import PortForwarder

forwarder = PortForwarder(8080, "remote.example.com", 80)
forwarder.start()
```

`start()` blocks. Call `stop()` from another thread to close the
listener and in-flight sockets. Pass `local_port=0` to ask the OS for
an ephemeral port, then read `bound_port` after `on_ready` fires:

```python
from threading import Event, Thread

from lupaxa.port_forwarder import PortForwarder

ready = Event()
with PortForwarder(0, "127.0.0.1", 9000, connect_timeout=2.5) as forwarder:
    thread = Thread(target=forwarder.start, kwargs={"on_ready": ready.set}, daemon=True)
    thread.start()
    ready.wait()
    print(forwarder.bound_port)
```

Several mappings can share a `PortForwarderGroup`. Leaving a `with`
block calls `stop()`.
