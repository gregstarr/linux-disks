import subprocess
import re

blkid_output = subprocess.run("blkid", shell=True, capture_output=True).stdout.decode()
df_output = subprocess.run("df -h", shell=True, capture_output=True).stdout.decode()
fdisk_output = subprocess.run("fdisk -l", shell=True, capture_output=True).stdout.decode()
with open("/etc/fstab") as f:
    fstab = f.read()

starts = [match.start() for match in re.finditer("Disk /dev/sd", fdisk_output)]
strings = []
for i in range(len(starts)):
    if i == len(starts) - 1:
        strings.append(fdisk_output[starts[i]:])
    else:
        strings.append(fdisk_output[starts[i]:starts[i+1]])

disks = {}
for s in strings:
    disk =  s[s.find("Disk ")+5:s.find(":")]
    size = s[s.find(":")+1:s.find(",")]
    model_start = s.find("Disk model") + 12
    model = s[model_start:model_start + s[model_start:].find("\n")].strip()
    parts = re.findall(f"{disk}\d+", s)
    disks[disk] = {'size': size, 'model': model, 'parts': {}}
    for p in parts:
        disks[disk]['parts'][p] = {}
        sob = re.search(f'{p} \s+\S+\s+\S+\s+\S+(\s+\S+)', fdisk_output)
        if sob is not None:
            disks[disk]['parts'][p]['size'] = sob.group(1).strip()
        sob = re.search(f'{p}: UUID="(.+?)"', blkid_output)
        if sob is not None:
            uuid = sob.group(1)
            disks[disk]['parts'][p]['uuid'] = uuid
            sob = re.search(f'/dev/disk/by-uuid/{uuid} (\S+)', fstab)
            if sob is not None:
                disks[disk]['parts'][p]['mount'] = sob.group(1)

smn = [f'/mnt/s{n}' for n in range(1, 100)]
bmn = [f'/mnt/l{n}' for n in range(1, 100)]

for disk, data in disks.items():
    for p, part in data['parts'].items():
        print(p, part)
        if 'sda' in p:
            continue
        if 'mount' in part:
            if 'T' in part['size']:
                bmn.remove(part['mount'])
            else:
                smn.remove(part['mount'])

parts = {}
for disk, data in disks.items():
    for p, part in data['parts'].items():
        if 'sda' in p:
            continue
        print(p)
        print(part)
        if 'mount' in part:
            dmnt = part['mount']
        elif 'T' in part['size']:
            dmnt = bmn[0]
        else:
            dmnt = smn[0]
        new_mount = input(f"Enter new mount ({dmnt}): ")
        if new_mount == "":
            new_mount = dmnt
        part['mount'] = new_mount
        parts[p] = part
        if new_mount in smn:
            smn.remove(new_mount)
        if new_mount in bmn:
            bmn.remove(new_mount)

for p, part in parts.items():
    print(p, part)


new_fstab = f"""# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
/dev/disk/by-uuid/{disks['/dev/sda']['parts']['/dev/sda2']['uuid']} / ext4 defaults 0 0
/swap.img       none    swap    sw      0       0

"""

for p, part in parts.items():
    new_fstab += f"/dev/disk/by-uuid/{part['uuid']} {part['mount']} ext4 defaults 0 0\n"

with open('fstab_test', 'w') as f:
    f.write(new_fstab)
