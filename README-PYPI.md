<!-- markdownlint-disable -->
<p align="center">
  <a href="https://github.com/lupaxa-sre-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/sre-toolbox/readme-logo.png" alt="Project Logo" width="256"/><br/>
  </a>
</p>
<h3 align="center">
  The Lupaxa SRE Toolbox<br />
  Part of The Lupaxa Project
</h3>

<br />

# lupaxa-port-forwarder

Listen on a local TCP port and forward each connection to a remote
host and port.

## Features

- Listen on a local TCP port (loopback by default)
- Forward each accepted client to a remote host and port
- One process can run several `LOCAL:HOST:REMOTE` mappings
- Relay bytes in both directions until either side closes
- Half-close one side without dropping the reply on the other
- `--bind` to choose the local listen address (`0.0.0.0` to share on the LAN)
- `--allow` to restrict source addresses and CIDR networks
- `--max-connections` and `--idle-timeout` to cap sessions
- `--timeout` to bound the remote connect
- `--verbose` / `--quiet` for log volume
- Library API (`PortForwarder`, `PortForwarderGroup`) and CLI (`port-forwarder`)
- Fully typed, linted, formatted, and tested
- No runtime dependencies beyond the standard library

## Installation

### From PyPI

```bash
pip install lupaxa-port-forwarder
```

### From source (development mode)

```bash
pip install -e ".[dev]"
```

Requires Python 3.13+. No runtime dependencies.

## Library quick start

```python
from lupaxa.port_forwarder import PortForwarder

with PortForwarder(8080, "remote.example.com", 80) as forwarder:
    forwarder.start()
```

## CLI quick start

```bash
port-forwarder --help
port-forwarder 8080 remote.example.com 80
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
port-forwarder 8080 remote.example.com 80 --bind 0.0.0.0 --allow 10.0.0.0/8
port-forwarder 8080 remote.example.com 80 --max-connections 8 --idle-timeout 60
```

You can also run the CLI as a module:

```bash
python -m lupaxa.port_forwarder --help
python -m lupaxa.port_forwarder --version
```

## Documentation

Online documentation:

[Documentation](https://port-forwarder.thelupaxaproject.org/)

Source repository:

[GitHub](https://github.com/lupaxa-sre-toolbox/port-forwarder)

### Serve docs locally

From a clone of the repository:

```bash
make mkdocs-serve
```

Then open the local URL printed by MkDocs in your browser.

## Development

Clone the repository and install with Make:

```bash
make init                # first-time makefile-skills checkout
make python-install-dev  # editable install with [dev]
make python-check        # lint, type-check, and test
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
