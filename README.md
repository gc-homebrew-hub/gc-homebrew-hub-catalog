# gc-homebrew-hub-catalog

The list of GameCube homebrew that
[GC Homebrew Hub Browser](https://github.com/gc-homebrew-hub/gc-homebrew-hub-browser)
offers to install. The program reads two files from this repository's `main`
branch:

- `sources.json`: the default sources every console starts with.
- `index.json`: the apps in this source.

To add or update an app, open a pull request that changes `index.json`. A
check runs `scripts/validate.py --download` on every pull request: it applies
the same rules as the program and downloads each app to confirm its size and
SHA-256.

## An app entry

```json
{
  "slug": "cubebrowser",
  "name": "CubeBrowser",
  "author": "Arial-Bold",
  "version": "2.8",
  "category": "utilities",
  "short": "Web browser with HTTPS, downloads and MIDI music",
  "long": "A longer description shown on the app's page.",
  "homepage": "https://github.com/Arial-Bold/Cubebrowser",
  "zip": "https://github.com/Arial-Bold/Cubebrowser/releases/download/v2.8/cubebrowser.zip",
  "zip_size": 1018530,
  "sha256": "1e3751a5...",
  "root": "cubebrowser",
  "binary": "default.dol",
  "folder": "cubebrowser",
  "keep": ["gcbrowser"],
  "updated": 1793317503
}
```

| Field | Required | Meaning |
|---|---|---|
| `slug` | yes | Unique id: 1-31 of `a-z`, `0-9`, `-`. |
| `name`, `author`, `version` | yes | Shown in the list. Dotted numeric versions compare numerically; any other change of version counts as an update. |
| `category` | yes | One of `games`, `emulators`, `media`, `utilities`, `demos`. |
| `short` | yes | One line, at most 95 characters. |
| `long` | no | The app's page, at most 1023 characters. |
| `homepage` | no | Project page. |
| `zip` or `dol` | one of them | Download address: a zip, or a bare `.dol`. Use a release asset of a fixed version, never a "latest" link, so the SHA-256 stays true. |
| `zip_size` | recommended | Download size in bytes. |
| `sha256` | recommended | SHA-256 of the download; the install fails if it does not match. |
| `root` | no | Folder inside the zip whose contents become the app's folder. |
| `binary` | no | The program inside the app's folder, default `boot.dol`. For a bare `.dol`, the file name to save it as. |
| `folder` | no | Folder under `sd:/apps/`, default the slug. |
| `keep` | no | Up to 4 paths in the app's folder that an update leaves alone (settings, saves). |
| `copy_to_root` | no | Up to 4 folders from the app that are copied to the root of the card on first install, never overwritten, and left in place on removal. |
| `updated` | no | Release date as Unix time in seconds. |

Limits: 256 apps, and `index.json` at most 256 KB.

## Testing a change on a console

`scripts/serve.sh` serves this folder on your network and prints the address
to add on the console (Sources, X).

## Licence

The catalog files and scripts are under the [MIT License](LICENSE). The apps
it lists are not part of this repository and keep their own licences; see
each app's homepage.
