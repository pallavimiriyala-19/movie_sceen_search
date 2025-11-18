#!/usr/bin/env bash
# wait-for-it.sh: wait until a service is ready

host="$1"
shift
cmd="$@"

echo "Waiting for $host to be available..."
until nc -z ${host%:*} ${host#*:}; do
  sleep 2
  echo "Still waiting for $host..."
done

echo "$host is up — executing command"
exec $cmd
