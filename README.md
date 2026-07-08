# esphome-components

Custom [ESPHome](https://esphome.io/) components for my Home Assistant setup.

## Usage

```yaml
external_components:
  - source: github://yuhenghuang/esphome-components@main
```

## Components

| Component | Description | Used by |
|---|---|---|
| `gdey037z03` | GDEY037Z03 3.7" e-ink display driver | esp32-s3-eink-display |

## Migrating from local custom_components

These previously lived at `programming/esphome/custom_components/` on the dashboard host.
To switch from a local path to this repo, change the YAML from:

```yaml
external_components:
  - source:
      type: local
      path: custom_components
```

to:

```yaml
external_components:
  - source: github://yuhenghuang/esphome-components@main
```
