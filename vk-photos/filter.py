#!/usr/bin/env python
# if running in py3, change the shebang, drop the next import for readability (it does no harm in py3)
from collections import defaultdict
import hashlib
from pathlib import Path


def chunk_reader(fobj, chunk_size=1024):
    """Generator that reads a file in chunks of bytes"""
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            return
        yield chunk


def get_hash(filename: Path, first_chunk_only=False, hash=hashlib.sha1):
    hashobj = hash()
    with open(filename, "rb") as file_object:
        if first_chunk_only:
            hashobj.update(file_object.read(1024))
        else:
            for chunk in chunk_reader(file_object):
                hashobj.update(chunk)
        hashed = hashobj.digest()

        return hashed


def check_for_duplicates(path: Path) -> int:
    hashes_by_size = defaultdict(list)  # dict of size_in_bytes: [full_path_to_file1, full_path_to_file2, ]
    hashes_on_1k = defaultdict(list)  # dict of (hash1k, size_in_bytes): [full_path_to_file1, full_path_to_file2, ]
    hashes_full = {}   # dict of full_file_hash: full_path_to_file_string
    files = path.glob("*.jpg")

    for file_path in files:
        # if the target is a symlink (soft one), this will
        # dereference it - change the value to the actual target file
        file_size = file_path.stat().st_size
        hashes_by_size[file_size].append(file_path)


    # For all files with the same file size, get their hash on the 1st 1024 bytes only
    for size_in_bytes, files in hashes_by_size.items():
        if len(files) < 2:
            continue    # this file size is unique, no need to spend CPU cycles on it

        for filename in files:
            small_hash = get_hash(filename, first_chunk_only=True)
            # the key is the hash on the first 1024 bytes plus the size - to
            # avoid collisions on equal hashes in the first part of the file
            hashes_on_1k[(small_hash, size_in_bytes)].append(filename)

    duplicates = []

    # For all files with the hash on the 1st 1024 bytes, get their hash on the full file - collisions will be duplicates
    for __, files_list in hashes_on_1k.items():
        if len(files_list) < 2:
            continue    # this hash of fist 1k file bytes is unique, no need to spend cpy cycles on it

        for filename in files_list:
            full_hash = get_hash(filename, first_chunk_only=False)
            duplicate = hashes_full.get(full_hash)
            if duplicate:
                duplicates.append(filename)
            else:
                hashes_full[full_hash] = filename

    for file in duplicates:
        file.unlink()

    return len(duplicates)