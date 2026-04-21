# stories-mycontinuum.xyz

This project publishes a decentralized, Nostr-powered blog using GitHub Actions and GitHub Pages.

- Content source: Nostr kind:30023 events with `#continuum-stories` tag
- Build: Python script (`fetch_articles.py`) pulls + renders Markdown to HTML
- Deploy: GitHub Pages (`stories.mycontinuum.xyz`)
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)

## Quick start

This is not zero-setup. To use it for yourself, you’ll need your own GitHub account, your own repository, and a personal access token.
The setup takes a bit of initial effort, but once it’s in place the workflow is straightforward to run and adapt.
If there’s interest, I can simplify the first-run setup further.
