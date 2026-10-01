#!/usr/bin/env sh
# Regenerate the README images in .github/assets and the directory logos in assets/
# from their sources.
# Needs Google Chrome (override with CHROME=...), poppler's pdftoppm, and ReportLab.
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
assets="$repo/.github/assets"
card="file://$assets/src/card.html"
chrome=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}

shot() {
  # $1 output relative to the repo, $2 query string, $3 width, $4 height
  "$chrome" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --virtual-time-budget=10000 --window-size="$3,$4" \
    --screenshot="$repo/$1" "$card?$2" >/dev/null 2>&1
  echo "rendered $1"
}

shot .github/assets/banner-light.png "kind=banner&theme=light" 1280 440
shot .github/assets/banner-dark.png "kind=banner&theme=dark" 1280 440
shot .github/assets/social-preview.png "kind=social&theme=dark" 1280 640

# Plugin directory logos, 500x500. assets/composer-icon.svg is the same mark drawn
# by hand at composer size; change both together.
shot assets/logo.png "kind=icon&theme=light" 250 250
shot assets/logo-dark.png "kind=icon&theme=dark" 250 250

# The demo résumé comes from the real renderer, so the README always shows actual output.
demo=$(mktemp -d)
python3 "$repo/scripts/yapply.py" --root "$demo" demo >/dev/null
# Crop to the written part of the page; the demo résumé is intentionally short.
pdftoppm -png -r 150 -f 1 -l 1 -x 0 -y 0 -W 1275 -H 660 -singlefile \
  "$demo/.yapply/applications/northstar-platform-engineer/output/resume.pdf" "$assets/src/demo-resume-page"
rm -rf "$demo"
shot .github/assets/demo-light.png "kind=demo&theme=light" 1280 624
shot .github/assets/demo-dark.png "kind=demo&theme=dark" 1280 624
