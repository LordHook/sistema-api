#!/bin/bash
set -x

echo "Navigating to /api"
mkdir -p /api
cd /api

echo "Installing git"
dnf install git -y

echo "Cloning repository"
if [ -z "$(ls -A /api)" ]; then
    git clone git@github.com:LordHook/sistema-api.git .
else
    # In case there's something, we fetch and reset
    git init
    git remote add origin git@github.com:LordHook/sistema-api.git || true
    git fetch
    git checkout -f main
    git branch --set-upstream-to=origin/main main
fi

echo "Installing Python 3 and pip"
dnf install python3 python3-pip python3-devel gcc -y

echo "Configuring PostgreSQL 16 Repo"
dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-10-x86_64/pgdg-redhat-repo-latest.noarch.rpm
dnf -qy module disable postgresql || true

echo "Installing PostgreSQL 16"
dnf install -y postgresql16-server postgresql16-devel postgresql16-contrib

echo "Installing python requirements"
# We do this after installing pg devel packages just in case psycopg2 needs them
pip3 install -r requirements.txt || true

echo "Initializing PostgreSQL 16 database"
# postgresql-16-setup initdb will fail if already initialized, so we || true
/usr/pgsql-16/bin/postgresql-16-setup initdb || true

echo "Starting and enabling PostgreSQL 16 service"
systemctl enable --now postgresql-16

echo "DEPLOY_SUCCESS"
