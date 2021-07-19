sudo -u distillery psql -f pgsql/schema/authorization.sql
sudo -u distillery psql -f pgsql/schema/dashboard.sql
sudo -u distillery psql -f pgsql/schema/view.sql
sudo -u distillery psql -f pgsql/schema/query.sql
sudo -u distillery psql -f pgsql/schema/connection.sql
sudo -u distillery psql -f pgsql/schema/team_membership.sql
sudo -u distillery psql -f pgsql/schema/team.sql
sudo -u distillery psql -f pgsql/schema/user.sql

