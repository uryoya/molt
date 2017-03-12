#!/bin/sh
exec ssh -o IdentityFile=~/.ssh/molt_deploy_key -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "$@"
