#!/bin/bash

docker run --rm \
  -e PUBKEY=npub19wvckp8z58lxs4djuz43pwujka6tthaq77yjd3axttsgppnj0ersgdguvd \
  -v "$(pwd)/docs:/app/docs" \
  nostr-stories-my-continuum-fetcher

