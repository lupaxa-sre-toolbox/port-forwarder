<p align="center">
  <a href="https://github.com/lupaxa-sre-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/sre-toolbox/readme-logo.png" alt="SRE Toolbox" />
  </a>
</p>

<h1 align="center">Port Forwarder</h1>

Listen on a local TCP port and forward each connection to a remote
host and port.

## Install

```bash
pip install lupaxa-port-forwarder
port-forwarder --help
```

## CLI

```bash
port-forwarder 8080 remote.example.com 80
port-forwarder 8080:remote.example.com:80 5432:db.internal:5432
port-forwarder 8080 remote.example.com 80 --bind 0.0.0.0 --allow 10.0.0.0/8
port-forwarder 8080 remote.example.com 80 --max-connections 8 --idle-timeout 60
python -m lupaxa.port_forwarder --version
```

The tool binds a local TCP listener and relays each accepted client to
the remote host and port, copying bytes in both directions until either
side closes. Pass one `LOCAL HOST REMOTE` triple, or one or more
`LOCAL:HOST:REMOTE` mappings. By default it binds `127.0.0.1`. Use
`--bind 0.0.0.0` when other hosts must connect, and `--allow` to limit
who may. `--timeout` bounds the remote connect. `--max-connections` and
`--idle-timeout` cap concurrent sessions and quiet ones. The process
stays in the foreground and stops with `Ctrl+C` or `SIGTERM`.

## Library

```python
from lupaxa.port_forwarder import PortForwarder

with PortForwarder(8080, "remote.example.com", 80) as forwarder:
    forwarder.start()
```

## Development

```bash
make init
make python-install-dev
make python-check
make mkdocs-serve
```

## Documentation

The published guide is at
<https://port-forwarder.thelupaxaproject.org/>.

Site Markdown lives in `mkdocs/`.

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
