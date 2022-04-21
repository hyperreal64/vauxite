#!/usr/bin/env python3

import glob
import os
import selinux
import shutil
import subprocess

# Global variables
base_dir = os.getcwd()
working_dir = os.path.join(base_dir, "build")
treefile = os.path.join(base_dir, "src/vauxite.yaml")
lockfile = os.path.join(base_dir, "src/overrides.yaml")
ostree_cache_dir = os.path.join(working_dir, "cache")
ostree_repo_dir = os.path.join(working_dir, "vauxite")
srv_root = "/srv/ostree"
srv_repo_dir = os.path.join(srv_root, "vauxite")


# Exception handling function
def handle_exception(ex):
    if ex is shutil.Error or ex is OSError:
        exit_msg = "%s" % ex.strerror

    if ex is subprocess.CalledProcessError:
        exit_msg = "%s" % ex.stderr

    exit("💥 %s" % exit_msg)


# Check if running as root
if os.geteuid() != 0:
    exit("🔒️ Permission denied. Are you root?")


# Check if required commands exist
print("⚡️ Running preliminary checks...")

if shutil.which("ostree") is None:
    exit("💥 ostree is not installed")

if shutil.which("rpm-ostree") is None:
    exit("💥 rpm-ostree is not installed")


# Setup the build environment
print("🔨 Setting up build environment...")

if not os.path.exists(treefile):
    exit("💥 vauxite.yaml does not exist")

try:
    if os.path.exists(ostree_cache_dir):
        shutil.rmtree(ostree_cache_dir)

    if os.path.exists(ostree_repo_dir):
        shutil.rmtree(ostree_repo_dir)

    os.makedirs(ostree_cache_dir)
    os.makedirs(ostree_repo_dir)
    os.chown(working_dir, 0, 0)

except Exception as ex:
    handle_exception(ex)


# Initialize the OSTree repo
print("🌱 Initializing the OSTree repository at %s..." % ostree_repo_dir)

try:
    ostree = subprocess.run(
        ["ostree", "--repo=%s" % ostree_repo_dir, "init", "--mode=archive"],
        capture_output=True,
        check=True,
    )

except Exception as ex:
    handle_exception(ex)

# Build the ostree
print("⚡️ Building tree...")

try:
    if os.path.exists(lockfile) and os.path.getsize(lockfile) > 0:
        cmd_tail = "--ex-lockfile=%s %s" % (lockfile, treefile)
    else:
        cmd_tail = "%s" % treefile

    cmd_rpm_ostree = subprocess.run(
        [
            "rpm-ostree",
            "compose",
            "tree",
            "--unified-core",
            "--cachedir=%s" % ostree_cache_dir,
            "--repo=%s" % ostree_repo_dir,
            cmd_tail,
        ],
        check=True,
        text=True,
    )

except Exception as ex:
    handle_exception(ex)

# Generate the ostree summary
print("✏️ Generating summary...")

try:
    cmd_gen_summary = subprocess.run(
        ["ostree", "summary", "--repo=%s" % ostree_repo_dir, "--update"],
        check=True,
        text=True,
    )

except Exception as ex:
    handle_exception(ex)


# Move repository to web server root
print("🚚 Moving built repository to web server root...")

try:
    if not os.path.isdir(srv_root):
        os.makedirs(srv_root)

    if selinux.is_selinux_enabled():
        if os.path.isdir(srv_repo_dir):
            selinux.install(srv_repo_dir, srv_repo_dir + ".old")

        selinux.install(ostree_repo_dir, srv_root)
    else:
        if os.path.isdir(srv_repo_dir):
            shutil.move(srv_repo_dir, srv_repo_dir + ".old")

except Exception as ex:
    handle_exception(ex)

# Clean up
print("🗑️  Cleaning up...")

try:
    for dir in glob.glob("/var/tmp/rpm-ostree.*"):
        shutil.rmtree(dir)

except Exception as ex:
    handle_exception(ex)
