#!/bin/bash
set -e

cp /tmp/mongo-keyfile /data/keyfile
chmod 600 /data/keyfile

# Start mongod in the background
mongod --replSet rs0 --keyFile /data/keyfile --bind_ip_all &
pid="$!"

echo "🕒 Waiting for mongod to be available..."
sleep 5

echo "🚀 Initializing replica set..."
mongosh --eval '
try {
  rs.initiate({_id: "rs0", members: [{_id: 0, host: "localhost:27017"}]});
} catch(e) {
  if (!String(e).includes("already initialized")) throw e;
}
'

sleep 5

echo "👤 Creating admin user..."
mongosh --eval '
try {
  db = db.getSiblingDB("admin");
  db.createUser({
    user: "admin",
    pwd: "admin_password",
    roles: [{role: "root", db: "admin"}]
  });
} catch(e) {
  if (!String(e).includes("already exists")) throw e;
}
'

# Bring mongod back to foreground
wait $pid
