drop table if exists "team_membership" cascade;

create table if not exists "team_membership" (
	team_xid char(32) not null,
	user_xid char(32) not null,
	is_admin boolean not null default false,
	primary key(team_xid, user_xid),
	foreign key(team_xid) references "team"(xid),
	foreign key(user_xid) references "user"(xid)
);
