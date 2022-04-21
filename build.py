#!/usr/bin/env python3
# Usage: sudo ./build.py

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

# Check if running as root
if os.geteuid() != 0:
    exit("🔒️ Permission denied. Are you root?")

# Check if required commands exist
try:
    print("⚡️ Running preliminary checks...")

    if shutil.which("ostree") is None:
        exit("💥 ostree is not installed")

    if shutil.which("rpm-ostree") is None:
        exit("💥 rpm-ostree is not installed")

    # Setup the build environment
    print("🔨 Setting up build environment...")

    if not os.path.exists(treefile):
        exit("💥 vauxite.yaml does not exist")

    if os.path.exists(ostree_cache_dir):
        shutil.rmtree(ostree_cache_dir)

    if os.path.exists(ostree_repo_dir):
        shutil.rmtree(ostree_repo_dir)

    os.makedirs(ostree_cache_dir)
    os.makedirs(ostree_repo_dir)

    # Initialize the OSTree repo
    print("🌱 Initializing the OSTree repository at %s..." % ostree_repo_dir)

    subprocess.run(
        [
            "ostree",
            "--repo=%s" % ostree_repo_dir,
            "init",
            "--mode=archive",
        ],
        check=True,
        text=True,
    )

    # Build the ostree
    print("⚡️ Building tree...")

    if os.path.exists(lockfile) and os.path.getsize(lockfile) > 0:
        cmd_tail = "--ex-lockfile=%s %s" % (lockfile, treefile)
    else:
        cmd_tail = "%s" % treefile

    subprocess.run(
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
    print()

    # Generate the ostree summary
    print("✏️ Generating summary...")

    subprocess.run(
        ["ostree", "summary", "--repo=%s" % ostree_repo_dir, "--update"],
        check=True,
        text=True,
    )

    # Move repository to web server root
    print("🚚 Moving built repository to web server root...")

    if not os.path.isdir(srv_root):
        os.makedirs(srv_root)

    if selinux.is_selinux_enabled():
        if os.path.isdir(srv_repo_dir):
            selinux.install(srv_repo_dir, srv_repo_dir + ".old")

        selinux.install(ostree_repo_dir, srv_repo_dir)
        selinux.chcon(srv_repo_dir, "httpd_sys_content_t", recursive=True)
        selinux.chcon(srv_repo_dir, "httpd_sys_rw_content_t", recursive=True)
    else:
        if os.path.isdir(srv_repo_dir):
            shutil.move(srv_repo_dir, srv_repo_dir + ".old")

    # Clean up
    print("🗑️  Cleaning up...")

    for dir in glob.glob("/var/tmp/rpm-ostree.*"):
        shutil.rmtree(dir)

    shutil.rmtree(srv_repo_dir + ".old")

except (shutil.Error, subprocess.CalledProcessError, OSError) as e:
    if e is shutil.Error:
        print("💥 shutil.Error: %s" % e.strerror)
        exit(1)

    if e is subprocess.CalledProcessError:
        print("💥 subprocess.CalledProcessError: %s" % e.stderr)
        exit(1)

    if e is OSError:
        print("💥 OSError: %s" % e.strerror)
        exit(1)
