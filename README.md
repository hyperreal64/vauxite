# Vauxite

This is an immutable Fedora-based XFCE desktop. It uses [rpm-ostree](https://coreos.github.io/rpm-ostree/), [podman](https://podman.io/), and [toolbox](https://containertoolbx.org/) for container-focused development workflows.

There are currently no installer images, but Vauxite may be installed from an existing OSTree-based system like [Fedora Silverblue](https://silverblue.fedoraproject.org/) or [Fedora IoT](https://getfedora.org/en/iot/).

## Usage

Add my server URL as a new remote:

```bash
sudo ostree remote add --no-gpg-verify vauxite https://ostree.hyperreal.coffee
```

Pin the current tree in case something breaks during or after the rebase:

```bash
sudo ostree admin pin 0
```

Rebase the tree to Vauxite:

```bash
sudo rpm-ostree rebase vauxite:vauxite/f36/x86_64/base

```

In case of failure or breakage, rollback to the previous commit:

```bash
sudo rpm-ostree rollback
```

## System updates

A new Vauxite tree is built every Saturday.

To perform system updates:

```bash
sudo rpm-ostree update
```

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/N4N2CT2JG)
