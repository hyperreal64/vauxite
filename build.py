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
working_dir = os.path.join(base_dir, "build")
ostree_cache_dir = os.path.join(working_dir, "cache")
ostree_repo_dir = os.path.join(working_dir, "repo")
srv_repo_dir = "/srv/ostree/vauxite"
no_changes = False


# subprocess.CalledProcessError handler
def handle_cpe(cpe: subprocess.CalledProcessError):
    print("💥 CalledProcessError")
    print("Command: %s" % cpe.cmd)
    if cpe.output:
        print("Output: %s" % cpe.output)
    if cpe.returncode:
        print("Return code: %d" % cpe.returncode)
    exit(1)


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
if not os.path.exists(ostree_cache_dir):
    os.makedirs(ostree_cache_dir)
if not os.path.exists(ostree_repo_dir):
    os.makedirs(ostree_repo_dir)

# Initialize the new OSTree repo if it is empty
try:
    if not os.listdir(ostree_repo_dir):
        print("🌱 Initializing the OSTree repository at %s..." % ostree_repo_dir)
        subprocess.run(
            [
                "ostree",
                "--repo=%s" % ostree_repo_dir,
                "init",
                "--mode=archive-z2",
            ],
            check=True,
            text=True,
        )
except subprocess.CalledProcessError as cpe:
    handle_cpe(cpe)

# Build the ostree
print("⚡️ Building tree...")
if os.path.exists(lockfile) and os.path.getsize(lockfile) > 0:
    cmd_tail = "--ex-lockfile=%s %s" % (lockfile, treefile)
else:
    cmd_tail = "%s" % treefile

try:
    cmd_build_tree = subprocess.run(
        [
            "rpm-ostree",
            "compose",
            "tree",
            "--unified-core",
            "--cachedir=%s" % ostree_cache_dir,
            "--repo=%s" % ostree_repo_dir,
            cmd_tail,
        ],
        capture_output=True,
        check=True,
        text=True,
    )

    if "No apparent changes since previous commit" in cmd_build_tree.stdout:
        no_changes = True
        print("💚 No apparent changes since previous commit")

except subprocess.CalledProcessError as cpe:
    handle_cpe(cpe)

if not no_changes:
    # Generate the ostree summary
    print("✏️ Generating summary...")

    try:
        subprocess.run(
            ["ostree", "summary", "--repo=%s" % ostree_repo_dir, "--update"],
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as cpe:
        handle_cpe(cpe)

    # Clean up
    print("🗑️  Cleaning up...")
    for dir in glob.glob("/var/tmp/rpm-ostree.*"):
        shutil.rmtree(dir, ignore_errors=True)

    # Use rsync to copy built repository to web server root
    print("🚚 Copying built repository to web server root")

    try:
        subprocess.run(
            ["rsync", "-aAX", "%s/" % ostree_repo_dir, srv_repo_dir],
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as cpe:
        handle_cpe(cpe)

    # Change SELinux context to httpd_sys_content_t and httpd_sys_rw_content_t
    if selinux.is_selinux_enabled():
        try:
            subprocess.run(
                ["chcon", "-t", "httpd_sys_content_t", srv_repo_dir, "-R"],
                check=True,
                text=True,
            )

            subprocess.run(
                ["chcon", "-t", "httpd_sys_rw_content_t", srv_repo_dir, "-R"],
                check=True,
                text=True,
            )
        except subprocess.CalledProcessError as cpe:
            handle_cpe(cpe)
