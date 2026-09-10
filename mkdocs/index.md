# Port Forwarder

`lupaxa-port-forwarder` is a small TCP relay. It listens on a local
port and forwards each accepted connection to a remote host and port.

Install the package for the library API and the `port-forwarder`
console command:

```bash
pip install lupaxa-port-forwarder
port-forwarder 8080 remote.example.com 80
```

You can also run `python -m lupaxa.port_forwarder`.

## What it does

- Binds a local TCP listener (loopback by default)
- Accepts each client on its own thread
- Opens a matching connection to the remote host and port
- Copies bytes in both directions until either side closes
- Keeps the other direction open after a half-close so replies still arrive
- Can run several `LOCAL:HOST:REMOTE` mappings in one process
- Optionally allowlists sources, caps concurrent sessions, and closes idle ones
- Exposes `PortForwarder` and `PortForwarderGroup` as library classes

## Next steps

- [Getting started](getting-started.md) — install and first run
- [Usage](usage.md) — CLI flags and the library API
- [Reference](reference.md) — arguments, defaults, and exit codes
- [Examples](examples.md) — common forward recipes
