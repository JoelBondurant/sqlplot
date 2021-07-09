drop table if exists "team_membership";

create table if not exists "team_membership" (
	id serial primary key,
	team_xid char(32) not null,
	user_xid char(32) not null,
	is_admin boolean not null default false,
);
