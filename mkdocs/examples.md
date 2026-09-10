# Examples

## Forward a local HTTP port

```bash
port-forwarder 8080 remote.example.com 80
```

Then open `http://127.0.0.1:8080/` in a browser or with `curl`.

## Reach an internal database from this machine

```bash
port-forwarder 5432 db.internal 5432
```

Connect your local client to `127.0.0.1:5432`.

## Forward two ports in one process

```bash
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
```

## Share the listener on the LAN

```bash
port-forwarder 8080 remote.example.com 80 --bind 0.0.0.0 --allow 10.0.0.0/8
```

Other hosts in `10.0.0.0/8` can now connect to this machine's address
on port `8080`. Repeat `--allow` for more networks.

## Cap sessions and close idle ones

```bash
port-forwarder 8080 remote.example.com 80 --max-connections 8 --idle-timeout 60
```

## Bound the remote connect

```bash
port-forwarder 8080 remote.example.com 80 --timeout 2.5 --quiet
```

## Library

```python
from lupaxa.port_forwarder import PortForwarder, PortForwarderGroup

http = PortForwarder(8080, "remote.example.com", 80, bind_host="127.0.0.1")
db = PortForwarder(5432, "db.internal", 5432, max_connections=4)
with PortForwarderGroup([http, db]) as group:
    try:
        group.start()
    except KeyboardInterrupt:
        group.stop()
```
