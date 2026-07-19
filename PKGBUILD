# Maintainer: Artem
pkgname=alarm-tui
pkgver=1.0.0
pkgrel=1
pkgdesc="A minimal, self-contained terminal alarm clock with a TUI, synthesized embedded audio, and a scrambled-code dismissal mechanic"
arch=('any')
url="https://github.com/spark900/ScramAlarm"
license=('MIT')
depends=(
  'python'
  'python-textual'    # AUR: github.com/Textualize/textual packaged as python-textual
  'python-rich'       # official [extra]
  'python-simpleaudio' # AUR: playback backend, links against alsa-lib
  'tmux'              # used by the systemd --user unit to host the TUI in the background
  'alsa-lib'           # official [extra]: runtime audio backend for python-simpleaudio
)
makedepends=(
  'python-build'
  'python-installer'
  'python-wheel'
  'python-setuptools'
)
optdepends=(
  'libnotify: for users who add their own desktop-notification hooks around alarm-tui'
)
backup=()
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')  # replace with the real checksum once you cut a release tarball

build() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl

  install -Dm644 systemd/alarm-tui.service \
    "$pkgdir/usr/lib/systemd/user/alarm-tui.service"

  install -Dm644 README.md \
    "$pkgdir/usr/share/doc/$pkgname/README.md"

  install -Dm644 LICENSE \
    "$pkgdir/usr/share/licenses/$pkgname/LICENSE" 2>/dev/null || true
}
