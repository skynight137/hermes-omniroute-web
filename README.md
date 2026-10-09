# hermes-omniroute-web

Hermes web search + extract backend that routes through an [OmniRoute](https://github.com/diegosouzapw/OmniRoute) gateway.

- `web_search` → OmniRoute `POST /api/v1/search`
- `web_extract` → OmniRoute `POST /api/v1/web/fetch`

OmniRoute holds the upstream provider keys and rotates them. This plugin only needs the gateway URL and key.

## Install

```bash
hermes plugins install skynight137/hermes-omniroute-web
```

Set the two variables (in the profile `.env`, or your shell):

```bash
OMNIROUTE_API_URL=https://your-omniroute-host/v1
OMNIROUTE_API_KEY=your-omniroute-key
```

Then select the provider in `config.yaml`:

```yaml
web:
  search_backend: omniroute
  extract_backend: omniroute
```

## Fallback

If OmniRoute is unreachable or unconfigured, the plugin returns `success: false` with the reason, so Hermes can fall through to its built-in providers.

## Verify

```bash
hermes plugins validate .
```

## Tested

Against a live OmniRoute gateway: search returned ranked results; fetch returned page content; a stopped gateway returned a clean `success: false`.
