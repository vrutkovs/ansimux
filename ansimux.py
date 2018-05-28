import argparse
import os
import subprocess
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

_CHECK_SESSION = "tmux has-session 2> /dev/null "
_NEW_SESSION = "tmux new-session -d -n {name} '{ssh}'"
_NEW_WINDOW = "tmux new-window -n {name} '{ssh}'"


def tmux_format():
    yield " ".join(
        [_CHECK_SESSION, "&&", _NEW_WINDOW, '||', _NEW_SESSION, ])
    while True:
        yield _NEW_WINDOW


def tmux_command(group_name='all', hosts=[], session=None, hostfile='hosts'):
    session = session or os.path.basename(os.path.abspath('.'))
    tmux = tmux_format()
    commands = []

    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=hostfile)

    if group_name not in inventory.groups:
        raise ValueError("No group '{}' found in {}".format(group_name, hostfile))

    group = inventory.groups[group_name]
    group_vars = group.get_vars()
    hosts = group.get_hosts()
    for host in hosts:
        # Combine group and host vars
        all_host_vars = group_vars.copy()
        all_host_vars.update(host.vars)

        user = all_host_vars.get('ansible_ssh_user', '')
        if not user:
            user = all_host_vars.get('ansible_user', '')
        hostname = all_host_vars.get('ansible_host', host.name)

        ssh = 'ssh {user}{host}'.format(
            user=user and user + '@' or '',
            host=hostname,
        )
        commands.append(next(tmux).format(ssh=ssh, name=host.name,))

    return commands

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Open tmux session with ssh to all hosts in the Ansible inventory.')
    parser.add_argument('hosts', nargs='*', help='hosts list')
    parser.add_argument('--group', help="host group", default="all")
    parser.add_argument('--inventory', help="host file", default="/etc/ansible/hosts")
    parser.add_argument('--dry-run', help="dry run: don't run tmux command")

    args = parser.parse_args()
    tmux_cmd = tmux_command(group_name=args.group, hosts=args.hosts, hostfile=args.inventory)
    print(" && ".join(tmux_cmd))
    if not args.dry_run:
        print("running {}".format(tmux_cmd))
        for cmd in tmux_cmd:
            subprocess.call(cmd, shell=True)
