#!/bin/bash
set -x

echo "Fixing PostgreSQL 16 Installation"
dnf install -y postgresql16-server

echo "Initializing database"
/usr/pgsql-16/bin/postgresql-16-setup initdb

echo "Enabling service"
systemctl enable --now postgresql-16

echo "PostgreSQL setup complete!"
