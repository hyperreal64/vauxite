#!/usr/bin/env python3
# Usage: sudo ./build.py

import glob
import os
import selinux
import shutil
import subprocess


# Global variables
base_dir = os.getcwd()
treefile = os.path.join(base_dir, "src/vauxite.yaml")
lockfile = os.path.join(base_dir, "src/overrides.yaml")
ostree_cache_dir = "/var/cache/ostree"
srv_root = "/srv/ostree"
ostree_repo_dir = os.path.join(srv_root, "vauxite")
ostree_repo_tmpdir = os.path.join(srv_root, "vauxite.new")

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

    if os.path.exists(ostree_repo_tmpdir):
        shutil.rmtree(ostree_repo_tmpdir)
    os.makedirs(ostree_repo_tmpdir)

    if not os.path.exists(ostree_cache_dir):
        os.makedirs(ostree_cache_dir)

    # Initialize the new OSTree repo
    print("🌱 Initializing the OSTree repository at %s..." % ostree_repo_tmpdir)

    subprocess.run(
        [
            "ostree",
            "--repo=%s" % ostree_repo_tmpdir,
            "init",
            "--mode=archive-z2",
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
            "--repo=%s" % ostree_repo_tmpdir,
            cmd_tail,
        ],
        check=True,
        text=True,
    )
    print()

    # Generate the ostree summary
    print("✏️ Generating summary...")

    subprocess.run(
        ["ostree", "summary", "--repo=%s" % ostree_repo_tmpdir, "--update"],
        check=True,
        text=True,
    )

    # Move repository to web server root
    print("🚚 Moving built repository to web server root...")

    if selinux.is_selinux_enabled():
        if os.path.exists(ostree_repo_dir):
            shutil.rmtree(ostree_repo_dir)
        selinux.install(ostree_repo_tmpdir, ostree_repo_dir)
    else:
        shutil.move(ostree_repo_tmpdir, ostree_repo_dir)

    # Clean up
    print("🗑️  Cleaning up...")

    for dir in glob.glob("/var/tmp/rpm-ostree.*"):
        shutil.rmtree(dir)

    # Change SELinux context to httpd_sys_content_t and httpd_sys_rw_content_t
    if selinux.is_selinux_enabled():
        subprocess.run(
            ["chcon", "-t", "httpd_sys_content_t", ostree_repo_dir, "-R"],
            check=True,
            text=True,
        )

        subprocess.run(
            ["chcon", "-t", "httpd_sys_rw_content_t", ostree_repo_dir, "-R"],
            check=True,
            text=True,
        )

except shutil.Error as e:
    exit("💥 shutil.Error: %s" % e.strerror)
except subprocess.CalledProcessError as e:
    exit("💥 subprocess.CalledProcessError: %s" % e.stderr)
except OSError as e:
    exit("💥 OSError: %s" % e.strerror)
