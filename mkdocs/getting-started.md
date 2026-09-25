# Getting Started

## Requirements

- Python 3.13 or newer
- No runtime dependencies beyond the standard library

## Install

```bash
pip install lupaxa-port-forwarder
port-forwarder --help
```

Library import:

```python
from lupaxa.port_forwarder import PortForwarder

forwarder = PortForwarder(8080, "remote.example.com", 80)
```

Module entry point:

```bash
python -m lupaxa.port_forwarder --version
```

### From Source (Development)

```bash
make init
make python-install-dev
port-forwarder --version
```

## First Run

Pass the local listen port, the remote host, and the remote port:

```bash
port-forwarder 8080 remote.example.com 80
```

Or pass one or more `LOCAL:HOST:REMOTE` mappings:

```bash
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
```

The process stays in the foreground and logs each accepted client.
Stop it with `Ctrl+C` or `SIGTERM`. Use `--quiet` to hide accept
lines, or `--timeout` to bound the remote connect.

By default the listener binds `127.0.0.1`. Use `--bind 0.0.0.0` when
other hosts must connect to the local port, and `--allow` to restrict
who may. `--max-connections` and `--idle-timeout` cap concurrent
sessions and quiet ones.

## Makefile Helpers

```bash
make init                 # clone makefile-skills into .makefiles/
make python-install-dev   # editable install with [dev]
make python-check         # lint + type + test
make mkdocs-serve         # local docs site
```
