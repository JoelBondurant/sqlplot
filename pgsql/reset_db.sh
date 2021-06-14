sudo -u distillery psql -f pgsql/schema/connection.sql
sudo -u distillery psql -f pgsql/schema/query.sql
sudo -u distillery psql -f pgsql/schema/view.sql

