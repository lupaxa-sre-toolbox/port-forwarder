<p align="center">
  <a href="https://github.com/lupaxa-sre-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/sre-toolbox/readme-logo.png" alt="SRE Toolbox" />
  </a>
</p>

<h1 align="center">Port Forwarder</h1>

Listen on a local TCP port and forward each connection to a remote
host and port. Python 3.13 or newer; no runtime dependencies beyond
the standard library.

## Install

```bash
pip install lupaxa-port-forwarder
port-forwarder --help
```

## CLI

```bash
port-forwarder 8080 remote.example.com 80
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
port-forwarder 8080:[::1]:80
port-forwarder 8080 remote.example.com 80 --bind 0.0.0.0 --allow 10.0.0.0/8
port-forwarder 8080 remote.example.com 80 --max-connections 8 --idle-timeout 60
port-forwarder 8080 remote.example.com 80 --timeout 2.5 --quiet
python -m lupaxa.port_forwarder --version
```

Pass one `LOCAL HOST REMOTE` triple, or one or more `LOCAL:HOST:REMOTE`
mappings. IPv6 remotes use brackets. Shared flags apply to every
mapping. Each accepted client opens a new remote connection and relays
bytes both ways until either side closes. A half-close on one side
leaves the other direction open so the reply can still arrive.

By default the listener binds `127.0.0.1`. Use `--bind 0.0.0.0` when
other hosts must connect, and `--allow` (repeatable IP or CIDR) to
limit who may. IPv4-mapped IPv6 sources are compared as IPv4 against
`--allow`. `--timeout` bounds the remote connect; it is not the idle
timer. `--max-connections` and `--idle-timeout` cap concurrent
sessions and quiet ones. Listen and remote ports must be `1`–`65535`.

The process stays in the foreground. `Ctrl+C` or `SIGTERM` closes the
listen sockets, waits for in-flight relays, and exits `0`. A bind
failure or bad arguments print to stderr and exit `1`.

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

`--verbose` and `--quiet` cannot be combined. `--timeout` and
`--idle-timeout` must be greater than `0` when set.
`--max-connections` must be at least `1` when set.

## Examples

### Forward a Local HTTP Port

```bash
port-forwarder 8080 remote.example.com 80
```

Then open `127.0.0.1:8080` in a browser or with `curl`.

### Reach an Internal Database from This Machine

```bash
port-forwarder 5432 db.internal 5432
```

Connect your local client to `127.0.0.1:5432`.

### Forward Two Ports in One Process

```bash
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
```

### Forward to an IPv6 Remote

```bash
port-forwarder 8080:[::1]:80
```

### Share the Listener on the LAN

```bash
port-forwarder 8080 remote.example.com 80 --bind 0.0.0.0 --allow 10.0.0.0/8
```

Other hosts in `10.0.0.0/8` can now connect to this machine's address
on port `8080`. Repeat `--allow` for more networks.

### Cap Sessions and Close Idle Ones

```bash
port-forwarder 8080 remote.example.com 80 --max-connections 8 --idle-timeout 60
```

### Bound the Remote Connect

```bash
port-forwarder 8080 remote.example.com 80 --timeout 2.5 --quiet
```

### Run as a Module

```bash
python -m lupaxa.port_forwarder --version
```

## Library

```python
from lupaxa.port_forwarder import PortForwarder, PortForwarderGroup

with PortForwarder(8080, "remote.example.com", 80) as forwarder:
    forwarder.start()
```

`start()` blocks. Call `stop()` from another thread, or leave the
`with` block. Several mappings can share a `PortForwarderGroup`:

```python
http = PortForwarder(8080, "remote.example.com", 80, bind_host="127.0.0.1")
db = PortForwarder(5432, "db.internal", 5432, max_connections=4)
with PortForwarderGroup([http, db]) as group:
    try:
        group.start()
    except KeyboardInterrupt:
        group.stop()
```

`local_port=0` asks the OS for an ephemeral port. Read `bound_port`
after `on_ready` fires:

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

## Development

```bash
make init
make python-install-dev
make python-check
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
