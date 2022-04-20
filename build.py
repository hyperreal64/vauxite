#!/usr/bin/env python3

import glob
import os
import shutil
import subprocess

# Check if running as root
if os.geteuid() != 0:
    exit("Permission denied. Are you root?")


# Check if required commands exist
print("⚡️ Running preliminary checks...")
if shutil.which("ostree") is None:
    exit("💥 ostree is not installed")

if shutil.which("rpm-ostree") is None:
    exit("💥 rpm-ostree is not installed")


# Setup the build environment
print("🔨 Setting up build environment...")
base_dir = os.getcwd()
working_dir = os.path.join(base_dir, "build")
treefile = os.path.join(base_dir, "src/vauxite.yaml")

if not os.path.exists(treefile):
    exit("💥 vauxite.yaml does not exist")

lockfile = os.path.join(base_dir, "src/overrides.yaml")
ostree_cache_dir = os.path.join(working_dir, "cache")
ostree_repo_dir = os.path.join(working_dir, "repo")

if os.path.exists(ostree_cache_dir):
    shutil.rmtree(ostree_cache_dir)

if os.path.exists(ostree_repo_dir):
    shutil.rmtree(ostree_repo_dir)

os.makedirs(ostree_cache_dir)
os.makedirs(ostree_repo_dir)
os.chown(working_dir, 0, 0)


# Initialize the OSTree repo
print("🌱 Initializing the OSTree repository at %s..." % ostree_repo_dir)
try:
    ostree = subprocess.run(
        ["ostree", "--repo=%s" % ostree_repo_dir, "init", "--mode=archive"],
        capture_output=True,
        check=True,
    )
except subprocess.CalledProcessError as cpe:
    print("💥 Error initializing OSTree repository at %s" % ostree_repo_dir)
    exit("%s" % cpe.stderr)


# Build the ostree
print("⚡️ Building tree...")
term_size = os.get_terminal_size()
print("=" * term_size.columns)

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
    print("=" * term_size.columns)
except subprocess.CalledProcessError as cpe:
    print("💥 Failed to build tree")
    print("=" * term_size.columns)
    exit(cpe.stderr)


# Generate the ostree summary
print("✏️ Generating summary...")
try:
    cmd_gen_summary = subprocess.run(
        ["ostree", "summary", "--repo=%s" % ostree_repo_dir, "--update"],
        check=True,
        text=True,
    )
except subprocess.CalledProcessError as cpe:
    print("💥 Failed to generate summary")
    exit(cpe.stderr)


# Clean up build environment and restore to pre-build state
print("🗑️ Cleaning up...")
# os.remove(buildinfo_file)
for dir in glob.glob("/var/tmp/rpm-ostree.*"):
    shutil.rmtree(dir)

sudo_user = os.environ["SUDO_USER"]
shutil.chown(working_dir, user=sudo_user, group=sudo_user)
