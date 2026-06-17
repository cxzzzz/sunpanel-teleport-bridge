# sunpanel-teleport-bridge

Sync SunPanel web cards to Teleport dynamic app resources.
The bridge runs a Teleport Application Service agent inside the container.

The first implementation is intentionally conservative:

- SunPanel is read-only.
- Teleport agent startup is skipped by default with `DRY_RUN=true`.
- The generated Teleport config is only rewritten when SunPanel data changes.
- SunPanel groups are mapped to Teleport labels, not UI folders.

## Portainer Git Stack

Deploy this repository as a Portainer stack using the Git repository option.
The repository root contains `docker-compose.yml` and `Dockerfile`, so Portainer
can build the image directly.

Set environment variables in Portainer:

```env
SUNPANEL_BASE_URL=http://192.168.100.106:3002
SUNPANEL_USERNAME=replace-me
SUNPANEL_PASSWORD=replace-me
TELEPORT_PROXY=192.168.100.106:3080
TELEPORT_JOIN_TOKEN=replace-me
TELEPORT_INSECURE_SKIP_VERIFY=false
TELEPORT_APP_USE_ANY_PROXY_PUBLIC_ADDR=true
DRY_RUN=true
TELEPORT_DATA_VOLUME=/opt/sunpanel-teleport-bridge/data
TELEPORT_CONFIG_VOLUME=/opt/sunpanel-teleport-bridge/config
```

Keep `DRY_RUN=true` until the generated plan looks correct.

## Commands

Probe SunPanel endpoints:

```bash
sunpanel-teleport-bridge probe
```

Run one dry-run sync and print the generated `teleport.yaml`:

```bash
sunpanel-teleport-bridge sync --once --dry-run
```

## SunPanel Access

The bridge logs in to the normal SunPanel panel API with username and password on
each run. It does not use SunPanel OpenAPI tokens.

Verified against SunPanel 1.8.1:

- `POST /api/login` returns a session token.
- `POST /api/panel/itemIcon/getListAllGroup` returns groups and their cards.
- Card `title`, `url`, `lanUrl`, and group `title` are enough to generate
  Teleport app resources.

Relevant configuration:

```env
SUNPANEL_BASE_URL=http://192.168.100.106:3002
SUNPANEL_USERNAME=replace-me
SUNPANEL_PASSWORD=replace-me
SUNPANEL_URL_FIELD=preferLanUrl
```

Run continuously:

```bash
sunpanel-teleport-bridge sync
```

## Teleport Setup

Create an Application Service join token in Teleport with the `app` role. The UI
usually gives a command shaped like this:

```bash
teleport configure \
  --app-name=example-app \
  --app-uri=http://localhost/ \
  --roles=app \
  --token=<token> \
  --proxy=192.168.100.106:3080 \
  --data-dir=/var/lib/teleport
```

Use the token value as `TELEPORT_JOIN_TOKEN` and the proxy as `TELEPORT_PROXY`.
The join token is only needed the first time the agent joins the cluster.
Keep `TELEPORT_DATA_VOLUME` persistent; it stores the joined agent identity.
If your self-hosted Teleport proxy uses a certificate that does not match
`TELEPORT_PROXY`, set `TELEPORT_INSECURE_SKIP_VERIFY=true`. Prefer a proper
certificate or matching DNS name for long-term use.

For deployments where the Application Service connects to Teleport over an
internal proxy address, but users open the Web UI through a public address, keep:

```env
TELEPORT_APP_USE_ANY_PROXY_PUBLIC_ADDR=true
```

This lets Teleport build app launch URLs from the public address used by the Web
UI, while the agent still connects to `TELEPORT_PROXY` over the internal network.
The compose file also uses `network_mode: host` to avoid Docker bridge subnets
overlapping common home LAN ranges such as `192.168.100.0/24`.

When `DRY_RUN=false`, the bridge:

1. Logs in to SunPanel.
2. Generates `/etc/teleport/sunpanel-apps.yaml`.
3. Starts `teleport start --config=/etc/teleport/sunpanel-apps.yaml`.
4. Rewrites the config and restarts the Teleport agent only when SunPanel apps
   change.
