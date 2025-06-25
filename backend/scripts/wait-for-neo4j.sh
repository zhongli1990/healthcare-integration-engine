#!/bin/sh
# wait-for-neo4j.sh

set -e

host="$1"
shift
cmd="$@"

until cypher-shell -u neo4j -p healthcare123 "RETURN 1" &>/dev/null; do
  >&2 echo "Neo4j is unavailable - sleeping"
  sleep 2
done

>&2 echo "Neo4j is up - executing command"
exec $cmd
